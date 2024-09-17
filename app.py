from flask import Flask, request, render_template, redirect, url_for, session
import pandas as pd
import google.generativeai as genai
import re
import os

app = Flask(__name__)
import secrets
secret_key = secrets.token_hex(16)  # Generates a 32-character hexadecimal key

app.secret_key = secret_key
print(app.secret_key)


# Configure API key
api_key = "AIzaSyDHj6EVSp6NCX2AidYbOH5sfBMvnhoTofc"
genai.configure(api_key=api_key)

# Create the model
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Prepare initial chat history for analysis
history = [
    {
        "role": "user",
        "parts": [
            """You are an expert WhatsApp promotional message analyzer with a deep understanding of marketing psychology and digital communication trends. Your task is to provide insightful, nuanced analyses of promotional messages sent via WhatsApp. These messages are typically short, informal, and designed to prompt quick action from recipients.

                For the following message, conduct a comprehensive yet concise analysis:

                {message}

                Break down your analysis into these key components:

                **Tone**:
                Describe the overall emotional tone of the message in one to two sentences. Consider aspects such as formality level, friendliness, urgency, and enthusiasm. Is it casual and conversational, or more professional and reserved? Does it create a sense of excitement or FOMO (fear of missing out)?

                **Writing Style**:
                Analyze the linguistic and structural elements of the message:
                - Sentence structure: Are sentences short and punchy, or more complex? Is there a mix?
                - Vocabulary: Assess the level of language used. Is it simple and accessible, or more sophisticated? Note any industry-specific jargon or trendy expressions.
                - Notable features: Identify any standout stylistic elements such as:
                • Use of emojis or emoticons
                • Abbreviations or text speak
                • Capitalization for emphasis
                • Repetition or rhyming
                • Use of questions or exclamations

                **Target Audience**:
                Infer the intended audience based on the message content, tone, and style. Consider:
                - Age group: Is it aimed at younger users, professionals, or a broader demographic?
                - Interests: What hobbies, lifestyles, or values does the message appeal to?
                - Occupation or life stage: Is it targeted at students, working professionals, parents, etc.?
                Provide your assessment in 1-2 concise sentences.

                **Key Message**:
                Distill the core purpose of the promotional message into one clear, concise sentence. What's the main point or primary call-to-action? Is it to inform about a sale, encourage app downloads, promote a new product, or something else?

                **Emotional Appeal**:
                Identify the primary emotion or psychological trigger the message aims to evoke. Common appeals in marketing include:
                - Excitement or joy (e.g., for a fun new product)
                - Urgency or FOMO (e.g., limited-time offers)
                - Trust or reliability (e.g., emphasizing product quality)
                - Empathy or belonging (e.g., shared experiences or values)
                Explain your assessment in 1-2 sentences, citing specific elements from the text that support this emotional appeal.

                **Effectiveness (Bonus Analysis)**:
                In 2-3 sentences, evaluate the potential effectiveness of the message. Consider how well the various elements (tone, style, targeting, key message, and emotional appeal) work together. Does the message seem likely to achieve its goal? Why or why not?

                Remember to keep your analysis clear, concise, and supported by specific examples from the text where relevant. Your insights should be valuable to marketers looking to understand and improve their WhatsApp promotional strategies."""
                        ],
                    },
                    {
                        "role": "model",
                        "parts": [
                            """Thank you for the comprehensive instructions. I understand my role as an expert WhatsApp promotional message analyzer with a focus on marketing psychology and digital communication trends. I'll provide a detailed yet concise analysis of the given message, breaking it down into the specified components: Tone, Writing Style, Target Audience, Key Message, Emotional Appeal, and the bonus Effectiveness evaluation.

                My analysis will be structured, insightful, and supported by specific examples from the text. I'll aim to offer valuable insights that could help marketers understand and enhance their WhatsApp promotional strategies.

                I'm ready to analyze the WhatsApp promotional message you provide."""
                        ],
                    }
                ]
chat_session = model.start_chat(history=history)

# Route to clear session memory and load the index page
@app.route('/')
def index():
    # Clear any session data when accessing the index page
    session.clear()
    return render_template('index.html')

def analyze_brand_messages(messages):
    # Concatenate all messages into one string
    all_messages = "\n".join(messages)
    analysis_request = f"""
                        "You are a marketing expert"
                        "Provide a comprehensive analysis of the following set of messages as a cohesive group:"
                        Analyze the following messages:
                        1. **Tone:** Briefly describe the overall tone (e.g., casual, formal).
                        2. **Writing Style:** Summarize sentence structure and vocabulary level.
                        3. **Target Audience:** Identify key demographics and interests.
                        4. **Top Emojis:** List the top 3 emojis used.
                        5. **Consistency:** Note any major inconsistencies in tone or style.
                        Keep responses to one sentence per category.
                        Messages:
                        {all_messages}
                        """

    try:
        # Send the concatenated messages for analysis as one block
        response = chat_session.send_message(analysis_request)
        analysis = response.text
        return "\n".join(line.strip() for line in analysis.splitlines() if line.strip())
    except KeyError:
        return "Error retrieving brand message analysis."


def bold_special_words(message):
    keywords = [
        r"\b\d{1,2}% off\b",
        r"\b\d+ days\b",
        r"\b\w+\sSale\b",
        r"\blimited\b",
        r"\bexclusive\b",
        r"\bfree\b",
        r"\btoday\b",
        r"\bnow\b",
        r"\boffer\b",
        r"\bexpires\b",
        r"\bhurry\b",
        r"\bdiscount\b",
        r"\bon\b",
    ]
    for keyword in keywords:
        message = re.sub(keyword, r"<b>\g<0></b>", message, flags=re.IGNORECASE)
    return message.replace('\n', '<br>')

def clean_message(message):
    # Remove extra single asterisks that are not used for bolding
    message = re.sub(r'(?<!\*)\*(?!\*)', '', message)  # Remove stray single asterisks
    
    # Ensure that asterisks used for bolding (**) are properly balanced
    # Remove asterisks used for bolding if they are unmatched
    message = re.sub(r'\*\*(?!.*\*\*)', '', message)  # Remove unmatched bolding asterisks
    
    return message.strip()

@app.route('/generate_message', methods=['POST'])
def generate_message():
    # Capture user inputs from the form
    tone_change = request.form.get('tone_change', '')
    tone_change_description = request.form.get('tone_change_description', '')
    occasion = request.form.get('occasion', '')
    other_occasion = request.form.get('other_occasion', '')
    discount = request.form.get('discount', '')
    other_discount = request.form.get('other_discount', '')
    campaign_type = request.form.get('campaign_type', '')

    # Handle 'other' values for occasion and discount
    occasion = other_occasion if occasion == 'other' and other_occasion else occasion
    discount = other_discount if discount == 'other' and other_discount else discount

    # Build the message generation request using the user input
    if tone_change == 'Yes':
        generation_request = (
            f"Generate a marketing message similar to the following examples. Apply the following adjustments to tone and style:\n\n"
            f"Examples:\nSample message 1\nSample message 2\n\n"
            f"Adjustments: {tone_change_description}\n"
            f"Occasion: {occasion}\n"
            f"Discount: {discount}\n"
            f"Campaign Type: {campaign_type}\n"
        )
    else:
        generation_request = (
            f"Generate a marketing message similar to the following examples while maintaining the same tone and style:\n\n"
            f"Examples:\nSample message 1\nSample message 2\n\n"
            f"Occasion: {occasion}\n"
            f"Discount: {discount}\n"
            f"Campaign Type: {campaign_type}\n"
            f"Please format the generated marketing message using Markdown syntax."
        )

    try:
        # Send the message generation request to the model
        response = chat_session.send_message(generation_request)
        generated_message = response.text

        # Bold special words and format the generated message
        formatted_message = bold_special_words(generated_message)

    except KeyError:
        formatted_message = "Error retrieving generated message."

    # Render the result in the template
    return render_template('result.html', result=formatted_message, original_message=format_response(generated_message))


@app.route('/improve_message', methods=['POST'])
def improve_message():
    user_message = request.form.get('user_message', '')
    feedback = request.form.get('feedback', '')

    if not user_message or not feedback:
        return redirect(url_for('compare_message'))  # Redirect if no message or feedback is provided

    # Improve message based on user feedback
    improvement_request = f"""Enhance the following message based on the provided feedback. Maintain the original message's core elements as follows:
                                1. Tone: Preserve the emotional feel and level of formality.
                                2. Structure: Keep the overall organization and flow of ideas.
                                3. Intent: Ensure the main purpose or call-to-action remains clear.

                                Guidelines for improvement:
                                - Address each point of feedback specifically.
                                - If the feedback contradicts maintaining tone, structure, or intent, prioritize the original message's characteristics.
                                - Aim for conciseness: Keep the improved message within 10% of the original word count.
                                - Enhance clarity and impact without changing the fundamental message.
                                - If applicable, optimize for WhatsApp's 1024 character limit for business messages.

                                Original Message:
                                {user_message}

                                Feedback to address:
                                {feedback}

                                Please provide:
                                1. The improved message
                                2. A brief explanation (2-3 sentences) of how the improvements address the feedback while maintaining the original message's essence.
                                """
    
    try:
        response = chat_session.send_message(improvement_request)
        improved_message = response.text
    except KeyError:
        improved_message = "Error retrieving improved message."

    # Bold special words in the improved message
    formatted_improved_message = bold_special_words(improved_message)

    return render_template(
        'improved_result.html',
        result=formatted_improved_message,
        original_message=format_response(user_message)
    )


@app.route('/compare_message', methods=['POST'])
def compare_message():
    user_message = request.form.get('user_message', '')

    # Ensure there's no interaction with any Excel data here
    if not user_message:
        return redirect(url_for('index'))  # Redirect if no message is provided

    # Comparison request to analyze the user's message
    comparison_request = f"""
                Analyze the following WhatsApp promotional message based on these quantitative criteria:

                1. Length:
                - Character count: [Insert number]
                - Score: 10 if ≤320, 8 if 321-640, 5 if 641-1024, 0 if >1024

                2. Call-to-Action (CTA):
                - Presence: Yes/No
                - Position: Beginning (1), Middle (2), End (3), or Not Present (0)
                - Score: Presence (0-5) + Position (0-5)

                3. Readability:
                - Flesch-Kincaid Grade Level: [Insert score]
                - Score: 10 if 6-8, 8 if 5 or 9, 5 if 4 or 10-11, 3 if 3 or 12-13, 0 if <3 or >13

                4. Opening Line Impact:
                - Word count of first sentence: [Insert number]
                - Score: 10 if ≤10 words, 8 if 11-15, 5 if 16-20, 3 if 21-25, 0 if >25

                5. Offer Clarity:
                - Position of main offer (sentence number): [Insert number]
                - Score: 10 if 1st, 8 if 2nd, 5 if 3rd, 3 if 4th, 0 if later or not clear

                Analysis Instructions:
                1. Provide the quantitative data for each criterion as indicated above.
                2. Calculate the score for each criterion based on the given scoring system.
                3. Calculate the overall score by taking the average of all five criteria scores.

                Overall Rating:
                - Excellent: 9-10
                - Good: 7-8.9
                - Average: 5-6.9
                - Poor: 3-4.9
                - Very Poor: 0-2.9

                Original Message:
                {user_message}

                Please provide your quantitative analysis followed by the overall rating.
                """

    
    try:
        response = chat_session.send_message(comparison_request)
        feedback = response.text
    except KeyError:
        feedback = "Error retrieving comparison feedback."

    # Analyzing tone and style of the user message
    tone_style_analysis_request = f"""Analyze the following message concisely:

                                    Message: {user_message}

                                    Provide a brief analysis in this format:

                                    1. Tone:
                                    - Overall emotional tone (e.g., formal, casual, enthusiastic, serious)
                                    - Mood conveyed (e.g., optimistic, cautionary, urgent)

                                    2. Writing Style:
                                    - Sentence structure (e.g., simple, complex, varied)
                                    - Vocabulary level (e.g., basic, advanced, technical)
                                    - Rhetorical devices used (e.g., metaphors, alliteration, rhetorical questions)
                                    - Any unique stylistic features

                                    3. Target Audience:
                                    - Likely intended audience (e.g., age group, profession, interest group)
                                    `   

                                    4. Purpose and Effectiveness:
                                    - Primary purpose of the message (e.g., inform, persuade, entertain)
                                    - How well the tone and style support this purpose
                                    

                                    Guidelines:
                                    - Keep each point clear, concise, and precise.
                                    - Use bullet points for clarity where appropriate.
                                    - Limit each section to 2-3 sentences or bullet points.
                                    - Avoid repetition and focus on the most salient features.
                                    - Do not include any extra line breaks between sections.
                                    """

    
    try:
        response = chat_session.send_message(tone_style_analysis_request)
        tone_style_analysis = response.text
    except KeyError:
        tone_style_analysis = "Error retrieving tone and style analysis."

    return render_template(
        'compare_result.html',
        feedback=format_response(feedback),
        tone_style_analysis=format_response(tone_style_analysis)
    )

def format_response(response_text):
    
    response_text = re.sub(r'#\s*#', '', response_text)
    
    # Convert bold text (e.g., **bold**) to <strong> tags
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response_text)

    # Replace newlines with <br> tags
    formatted_text = re.sub(r'\n', '<br>', formatted_text)

    # Convert list items (e.g., - item) to <li> tags
    formatted_text = re.sub(r'^- (.*?)(\n|$)', r'<li>\1</li>', formatted_text, flags=re.MULTILINE)

    # Wrap <li> items with <ul> tags
    # This is done in two steps to avoid wrapping <ul> tags multiple times
    list_items = re.findall(r'<li>.*?</li>', formatted_text)
    if list_items:
        formatted_text = re.sub(r'<li>.*?</li>', '<ul>' + ''.join(list_items) + '</ul>', formatted_text)

    return formatted_text



@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    session.clear()
    # Ensure previous analysis is cleared
    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file and file.filename.endswith('.xlsx'):
        # Read the new Excel file
        df = pd.read_excel(file)
        
        # Ensure that a valid 'Examples' column exists
        if 'Examples' in df.columns:
            messages = df['Examples'].tolist()
            analysis = analyze_brand_messages(messages)
            
            # Pass the analysis to the template as `excel_analysis` 
            return render_template('index.html', excel_analysis= format_response(analysis))
        else:
            return render_template('index.html', error_message="Uploaded Excel does not contain 'Examples' column.")

    # Redirect to the home page if the file format is invalid
    return redirect(url_for('index'))

@app.route('/improve_message_interactive', methods=['POST'])
def improve_message_interactive():
    user_message = request.form.get('generated_message', '')
    
    if not user_message:
        return redirect(url_for('index'))  # Redirect if no message is provided

    # Collect additional feedback from the user
    feedback = request.form.get('feedback', '')

    improvement_request = f"Improve this message while keeping its tone, structure, and intent intact. Consider the following feedback for improvement:\n\n{feedback}\n\n{user_message}"

    try:
        response = chat_session.send_message(improvement_request)
        improved_message = response.text

        # Format the improved message
        formatted_improved_message = bold_special_words(improved_message)

    except KeyError:
        formatted_improved_message = "Error retrieving improved message."

    return render_template('interactive_improve_result.html', result=formatted_improved_message, original_message=format_response(user_message))



if __name__ == '__main__':
    app.run(debug=True)
