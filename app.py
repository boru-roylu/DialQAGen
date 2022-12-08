import sys
sys.path.append('..')

import json
import os
import re

from flask import Flask, request, render_template, url_for, jsonify

import functions

app = Flask(__name__)

api_key_path = './.api_keys'
api_keys = []
with open(api_key_path, 'r') as f:
    for line in f:
        api_keys.append(line.strip())

@app.route('/gen')
def gen():
    paper_id = request.args.get('paper_id')
    iter_idx = request.args.get('iter_idx')

    paper_path = f'./data/papers/paper_{paper_id}.json'
    with open(paper_path, 'r') as f:
        paper = json.load(f)

    path = f'./data/dialog/paper_{paper_id}/{iter_idx}.json'
    with open(path, 'r') as f:
        data = json.load(f)
        dialog_history = data['dialog_history']
        questions = data['questions']

    return render_template(
        'generation.html',
        paper=paper,
        dialog_history=dialog_history,
        questions=questions)


@app.route('/regenerate', methods=['POST'])
def regenerate():
    if request.method == 'POST':
        res = request.json
        iter_idx = int(res['iter_idx']) + 1
        paper_id = int(res['paper_id'])

        last_turn = res['dialog_history'][-1]
        party = last_turn['party']

        dialog_history = res['dialog_history']
        print(dialog_history)
        print(party)

        if party == 'paragraph':
            response = functions.generate_summary(dialog_history, api_keys[0])
            party = 'summary'
        else:
            response = functions.generate_response(dialog_history, api_keys[0])
            party = 'agent'

        response = response.replace('\n', ' ')

        def filter_unicode(text):
            text = text.replace('\n', ' ')
            text = text.replace('\\u0027', '\'')
            text = text.replace('\"', ' ')
            text = text.encode("ascii", "ignore")
            text = text.decode()
            text = re.sub(r'[^\x00-\x7F]+',' ', text)
            text = text.strip('\"')
            return text

        response = filter_unicode(response) 

        agent_turn = {
            'party': party,
            'color': '#ADD8E6',
            'text': response,
        }

        dialog_history.append(agent_turn)

        questions = functions.generate_questions(dialog_history, api_keys[1])
        questions = list(map(filter_unicode, questions))

        data = {
            'dialog_history': dialog_history,
            'questions': questions,
        }

        os.makedirs(f'./data/dialog/paper_{paper_id}', exist_ok=True)
        path = f'./data/dialog/paper_{paper_id}/{iter_idx}.json'
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

        return jsonify(url_for("gen", iter_idx=iter_idx, paper_id=paper_id))
    else:
        raise ValueError('Only POST requests.')


if __name__ == '__main__':
    app.run(debug=True, threaded=True)