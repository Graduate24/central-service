import json

if __name__ == "__main__":
    with open('merge_result.json', 'r') as f:
        result = json.load(f)
        print(len(result))
        ml_result = list(filter(lambda x: x['from_ml'], result))
        print(len(ml_result))
        ml_detected_result = list(filter(lambda x: x['from_ml'] and x['ml_probability'] >= x['threshold_low'], result))
        print(len(ml_detected_result))
        print(ml_detected_result)
        detected_result = list(filter(lambda x: x['level'] != -1, result))
        print(len(detected_result))
        print(detected_result)
