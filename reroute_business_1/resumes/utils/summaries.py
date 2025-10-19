import random


GENERIC_SUMMARIES = [
    "A motivated and adaptable professional with a commitment to growth and continuous learning. Skilled in problem-solving and collaboration, ready to contribute to team success.",
    "Driven individual with strong communication and organizational skills. Recognized for reliability, determination, and the ability to excel in dynamic environments.",
    "Hardworking and focused candidate with a proven ability to learn quickly and adapt to new challenges. Dedicated to achieving results and adding value in every role.",
    "Dependable and resourceful professional with a strong foundation in teamwork and leadership. Committed to continuous improvement and positive impact in the workplace.",
    "Enthusiastic and goal-oriented candidate with a record of persistence and follow-through. Known for adaptability, resilience, and dedication to professional success.",
    "Results-driven individual with excellent interpersonal skills and a strong work ethic. Brings energy, determination, and a collaborative spirit to every opportunity.",
    "Focused professional recognized for problem-solving and critical thinking. Eager to apply skills and contribute meaningfully to team and organizational goals.",
    "Reliable and adaptable candidate with a strong sense of accountability. Demonstrates initiative and persistence in achieving both individual and team objectives.",
    "Positive and ambitious professional with strong communication abilities and a dedication to growth. Ready to embrace new challenges and opportunities for development.",
    "Committed and adaptable individual with proven teamwork skills and the ability to thrive under pressure. Brings determination and focus to achieving lasting results.",
]


def random_generic_summary() -> str:
    return random.choice(GENERIC_SUMMARIES)

