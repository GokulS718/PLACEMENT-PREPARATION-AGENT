import json
import random

companies = ['Amazon', 'Google', 'Microsoft', 'TCS', 'Infosys', 'Wipro', 'Meta', 'Apple', 'Cognizant', 'Accenture']
topics_coding = ['Arrays', 'Strings', 'Dynamic Programming', 'Trees', 'Graphs', 'Linked Lists', 'Sorting', 'System Design']
topics_apti = ['Probability', 'Time & Work', 'Percentages', 'Ratios', 'Logical Reasoning', 'Data Interpretation', 'Algebra']

def generate_coding_dataset():
    data = []
    for i in range(1, 501):
        target_comps = random.sample(companies, random.randint(1, 4))
        topic = random.choice(topics_coding)
        diff = random.choice(['Easy', 'Medium', 'Hard'])
        
        q = {
            "question_title": f"{topic} Problem {i}",
            "problem_description": f"This is a {diff.lower()} level {topic.lower()} question often asked in interviews. Solve it efficiently.",
            "difficulty": diff,
            "companies": target_comps,
            "topic_tags": [topic]
        }
        data.append(q)
    
    with open("coding_dataset.json", "w") as f:
        json.dump(data, f, indent=4)

def generate_apti_dataset():
    data = []
    for i in range(1, 501):
        target_comps = random.sample(companies, random.randint(1, 3))
        topic = random.choice(topics_apti)
        diff = random.choice(['Easy', 'Medium', 'Hard'])
        
        q = {
            "question_title": f"{topic} Aptitude {i}",
            "problem_description": f"Solve this {diff.lower()} {topic.lower()} problem within the time limit. Often asked by {target_comps[0]}.",
            "difficulty": diff,
            "companies": target_comps,
            "topic_tags": [topic]
        }
        data.append(q)
    
    with open("aptitude_dataset.json", "w") as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    generate_coding_dataset()
    generate_apti_dataset()
    print("Generated coding_dataset.json and aptitude_dataset.json with 500+ questions each.")
