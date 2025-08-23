import requests
import json
import re
# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    url = "https://darkermango.github.io/5-Letter-words/words.json"
    response = requests.get(url)
    words = response.json().get('words')

    _include = []
    _remaining = []
    for word in words:
        found = re.findall(r'\b(?=\w*o)(?=\w*u)(?=\w*n)(?!\w*o\w*u\w*n)\w+\b',word )
        if found:
            _include = _include + found

    for word in _include:
        found = re.findall(r'(?i)^(?!.*[slatepd]).+$', word)
        if found:
            _remaining = _remaining + found

    print(_remaining)