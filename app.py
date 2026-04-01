import os
import base64
import io
from flask import Flask, render_template, request, Response, stream_with_context
from google import genai
from dotenv import load_dotenv
import PyPDF2

# --- Initialization ---
load_dotenv()

app = Flask(__name__)

# Configure Google GenAI Client
API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=API_KEY)

# Global conversation memory
conversation_history = []

def extract_pdf_text(file_stream):
    """Simple PDF text extraction for context injection."""
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content: text += content + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF Extraction Error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Handle Multi-modal (Image/PDF + Text)
        user_message = ""
        image_data = None
        pdf_text = None
        mime_type = None
        model_name = request.form.get('model', 'Sonar')

        # Use the requested "gemini-2.5-flash"
        model_id = "gemini-2.5-flash" 

        if request.content_type.startswith('multipart/form-data'):
            user_message = request.form.get('message', '')
            if 'image' in request.files:
                file = request.files['image']
                mime_type = file.content_type
                
                if mime_type == 'application/pdf':
                    pdf_text = extract_pdf_text(io.BytesIO(file.read()))
                else:
                    image_data = file.read()
        else:
            data = request.json
            user_message = data.get('message', '')
            model_name = data.get('model', 'Sonar')

        if not user_message and not image_data and not pdf_text:
            return Response("No content provided", status=400)

        # Construct Parts for Multi-modal / Contextual Interaction
        parts = []
        
        # If PDF context is available, inject it into the message
        final_message = user_message
        if pdf_text:
            final_message = f"DOCUMENT CONTENT:\n{pdf_text}\n\nUSER QUESTION: {user_message}"
            
        if final_message: parts.append({"text": final_message})
        
        if image_data:
            parts.append({
                "inline_data": {
                    "data": base64.b64encode(image_data).decode('utf-8'),
                    "mime_type": mime_type
                }
            })

        # Track history
        conversation_history.append({"role": "user", "parts": parts})

        def generate_stream():
            try:
                system_instruction = (
                    f"You are Perplexity 2.5 Pro, an elite AI assistant. Style: Concisely professional. "
                    f"Mode: {model_name}. Use direct language, markdown formatting, and clear code blocks. "
                    "If PDF context is provided, prioritize it for accurate answers."
                )

                response_stream = client.models.generate_content_stream(
                    model=model_id,
                    contents=conversation_history,
                    config={'system_instruction': system_instruction}
                )
                
                full_response_text = ""
                for chunk in response_stream:
                    if chunk.text:
                        full_response_text += chunk.text
                        yield chunk.text

                conversation_history.append({"role": "model", "parts": [{"text": full_response_text}]})
                
            except Exception as e:
                error_msg = f"\n\n[Perplexity Error]: {str(e)}"
                if "404" in str(e) or "not found" in str(e).lower():
                    # Fallback to local stable model if 2.5 is not found
                    fallback_response = client.models.generate_content_stream(
                        model="gemini-2.0-flash",
                        contents=conversation_history,
                        config={'system_instruction': system_instruction}
                    )
                    full_fallback = ""
                    for fb_chunk in fallback_response:
                        if fb_chunk.text:
                            full_fallback += fb_chunk.text
                            yield fb_chunk.text
                    conversation_history.append({"role": "model", "parts": [{"text": full_fallback}]})
                else:
                    yield error_msg

        return Response(stream_with_context(generate_stream()), mimetype='text/plain')

    except Exception as e:
        print(f"Server Error: {e}")
        return Response(f"Internal Error: {str(e)}", status=500)

@app.route('/reset', methods=['POST'])
def reset():
    global conversation_history
    conversation_history.clear()
    return "Session reset", 200

if __name__ == '__main__':
    app.run(debug=True, port=8000)
