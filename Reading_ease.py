import textstat

def calculate_flesch_reading_ease(text):
    # Calculate the Flesch Reading Ease Score
    score = textstat.flesch_reading_ease(text)

    # Define the difficulty levels
    difficulty_levels = {
        (90, 100): "Very Easy",
        (80, 89): "Easy",
        (70, 79): "Fairly Easy",
        (60, 69): "Standard",
        (50, 59): "Fairly Difficult",
        (30, 49): "Difficult",
        (0, 29): "Very Confusing"
    }

    # Determine the difficulty level based on the score
    difficulty = None
    for score_range, level in difficulty_levels.items():
        if score >= score_range[0] and score <= score_range[1]:
            difficulty = level
            break

    # Return the result as a dictionary
    result = {
        "score": score,
        "difficulty": difficulty
    }
    return result

# Example usage:
text = "This is a sample text for testing readability."
result = calculate_flesch_reading_ease(text)
print(result)
