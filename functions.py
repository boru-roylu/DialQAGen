import openai
import time

NL_instruction = "An AI reading asistant can help with literature reviews. It can help you read papers efficeintly. It can summarize papers, explain the professional terms, answer questions, and even generate more questions that help you think more deeply about the papers. It helps students understand complex topics better.\n"
Greetings = "AGENT: I am your reading assistant! How may I help you today?\nUSER: I have trouble understanding this paper. Can you help me?\nAGENT: Sure! That's my job. I am happy to help you.\n"

template = """<p class="{party}" title="Reading_Assistant"> {turn} </p>"""

def get_response_from_codex(prompt, suffix, temperature, end_token='</p>'):
    done = False
    while not done:
        try:
            ret = openai.Completion.create(
                model="code-davinci-002",
                prompt=prompt,
                suffix=suffix,
                temperature=temperature,
                max_tokens=128,
                top_p=1,
                frequency_penalty=0.2,
                presence_penalty=0.2,
                stop=[end_token])
            done = True
        except Exception as exception:
            assert type(exception).__name__ == 'RateLimitError'
            # Adds sleep for the sake of preventing too frequent requst error.
            print('RateLimitError caught! Sleep 5 seconds')
            time.sleep(5)
        time.sleep(5)
    return ret.choices[0]['text'].strip()


def generate_summary(DH, key):
    openai.api_key = key
    context = ""
    for dict_ in DH:
        if dict_["party"] == "paragraph":
            context = dict_["raw_text"]
    if not context:
        print("No paragraph detected!")
        raise KeyboardInterrupt    
    
    prompt = "document:\n" + context+"\nsummarize the above in short:\n"
    print("prompt:" , prompt)
    summary = get_response_from_codex(prompt=prompt, suffix="", temperature=0)
  
    return summary

TEMPERATURE = 0.0

def generate_questions(DH, key, template=template):
    openai.api_key = key
    dialogue_history = ""
    context = ""
    duplication_detections = []

    asked_questions = []
    for dict_ in DH:
        if dict_["party"] == "paragraph":
            context = dict_["raw_text"]
        elif dict_["party"] == "summary":
            summary = dict_["text"]
        elif dict_["party"] == "user" and dict_["text"][-1] == "?":
            asked_questions.append(dict_["text"])
        elif dict_["party"] == "user":
            user_question = dict_["text"]
            dialogue_history += template.format(party="USER", turn=user_question)
            dialogue_history += "\n"
            duplication_detections.append(user_question)
        elif dict_["party"] == "answers" or dict_["party"] == "agent":
            agent_answer = dict_["text"]
            dialogue_history += template.format(party="AGENT", turn=agent_answer)
            dialogue_history += "\n"
            duplication_detections.append(agent_answer)

    if not asked_questions:
        asked_questions = [
            'What do the author(s) want to know (motivation)?',
            'Why was it done that way (context within the field)?',
            'How did the author(s) interpret the results (interpretation/discussion)?'
        ]
    
    question_prompt = "<question>\n"
    for q in asked_questions:
        question_prompt += f'{q}</question>\n'

    if not context:
        print("No paragraph detected!")
        raise KeyboardInterrupt

    prompt = NL_instruction 
    prompt += ("<paper_section> " + context + " <paper_section/>\n")
    prompt += ("<paper_summary> " + summary + " <paper_summary/>\n")
    prompt += dialogue_history 
    #prompt += '\n <p class="USER" title="Reading_Assistant"> Can you generate six questions about this paragraph for me? Please do not duplicate the information from the previous questions or the content we chatted about. </p>\n'
    prompt += '<p class="AGENT" title="Reading_Assistant"> Here are some questions I generated for you! </p>'
    prompt += question_prompt

    def generate_valid_question(prompt, temperature):
        question = None
        while question is None:
            question = get_response_from_codex(
                prompt=prompt, suffix="", temperature=temperature, end_token='</question>')
            question = question.strip()

            if not question:
                question = None
                continue

            if not question[0].isalpha() or question[-1] != '?':
                question = None
                continue
        return question

    prompt += '<question>'
    question1 = generate_valid_question(prompt, temperature=0.5)

    question_prompt += f'{question1}</question>\n'
    prompt += '<question>'
    question2 = generate_valid_question(prompt, temperature=0.6)

    #question_prompt += f'{question2}</question>\n'
    #prompt += '<question>'
    #question3 = generate_valid_question(prompt, temperature=0.8)

    print("="*100)
    print(f"{question1 = }")
    print(f"{question2 = }")
    print("="*100)

    #questions = list(set([question1, question2, question3]) - set(asked_questions))
    questions = list(set([question1, question2]) - set(asked_questions))

    return questions


def generate_response(DH, key, template=template):
    openai.api_key = key
    dialogue_history = ""
    context = ""
    for dict_ in DH:
        if dict_["party"] == "paragraph":
            context = dict_["raw_text"]
            continue
        elif dict_["party"] == "summary":
            summary = dict_["text"]
            continue
        elif dict_["party"] == "questions" or dict_["party"] == "user":
            user_question = dict_["text"]
            dialogue_history += template.format(party="USER", turn=user_question)
            dialogue_history += "\n"
        elif dict_["party"] == "answers" or dict_["party"] == "agent":
            agent_answer = dict_["text"]
            dialogue_history += template.format(party="AGENT", turn=agent_answer)
            dialogue_history += "\n"

    if not context:
        print("No paragraph detected!")
        raise KeyboardInterrupt

    prompt = NL_instruction 
    prompt += ("<paper_section> " + context + " <paper_section/>\n")
    prompt += ("<paper_summary> " + summary + " <paper_summary/>\n")
    #prompt += Greetings
    prompt += dialogue_history 
    prompt += """<p class="AGENT" title="Reading_Assistant"> """
    print(prompt)
    response = get_response_from_codex(prompt=prompt, suffix="", temperature=TEMPERATURE)

    print("="*100)
    print(response)
    print("="*100)

    return response