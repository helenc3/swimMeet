import re
from pathlib import Path
from openai import OpenAI
from common.utils import format_time_from_seconds
from pydantic import BaseModel, field_validator
from typing import Dict, Tuple

PREDICT_TIMES_DIR = Path(__file__).resolve().parent
SYSTEM_PROMPT_PATH = PREDICT_TIMES_DIR / "system_prompt.txt"

client = OpenAI()

# pydantic model for validating predictions
class Prediction(BaseModel):
    event: str
    time: float
    confidence: int
    
    @field_validator('time')
    @classmethod
    def validate_time(cls, v):
        if v <= 0:
            raise ValueError('Time must be positive')
        return v
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        if not isinstance(v, int) or v < 1 or v > 5:
            raise ValueError('Confidence must be an integer between 1 and 5')
        return v

class PredictedTimes(BaseModel):
    predictions: Dict[str, Tuple[float, int]]  # {event: (time, confidence)}
    
    @field_validator('predictions')
    @classmethod
    def validate_predictions(cls, v):
        for event, (time, confidence) in v.items():
            if time <= 0:
                raise ValueError(f'Time for {event} must be positive')
            if not isinstance(confidence, int) or confidence < 1 or confidence > 5:
                raise ValueError(f'Confidence for {event} must be an integer between 1 and 5')
        return v

# format best_times into a readable string for the prompt
def format_best_times_prompt(best_times):
    best_times_str = "Here are the short course yards best times for a swimmer:\n"
    for event, time in best_times.items():
        if time is not None:
            formatted_time = format_time_from_seconds(time)
            best_times_str += f"- {event}: {formatted_time} ({time:.2f} seconds)\n"
        else:
            best_times_str += f"- {event}: None (missing)\n"
    prompt = f"""{best_times_str}

Based on these times, predict the missing times. For each prediction, also provide a confidence score from 1-5 (integer only), where 1 is least confident and 5 is most confident. Format: Event : Time : Confidence"""
    return prompt

# Read system prompt from file
def load_system_prompt(file_path = SYSTEM_PROMPT_PATH):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using default system prompt.")
        return "You are an expert swimming coach." 

def parse_predictions_from_text(text: str, expected_events: list) -> PredictedTimes:
    """
    Parse predictions from text in format "Event : Time : Confidence" and validate.
    
    Args:
        text: Response text from LLM
        expected_events: List of events that should be predicted (where best_times[event] is None)
    
    Returns:
        PredictedTimes: Validated Pydantic model with predictions
    
    Raises:
        ValueError: If format is invalid or events don't match expected
    """
    predictions = {}
    
    # Parse lines in format "Event : Time : Confidence"
    # Try format with 3 colons first (Event : Time : Confidence)
    pattern = r'([^:]+):\s*([\d.]+)\s*:\s*(\d+)'
    matches = re.findall(pattern, text)
    
    if not matches:
        # Fallback: try format with 2 colons (Event : Time) - assume confidence 3 as default
        pattern_fallback = r'([^:]+):\s*([\d.]+)'
        matches_fallback = re.findall(pattern_fallback, text)
        if matches_fallback:
            matches = [(event, time, '3') for event, time in matches_fallback]
    
    if not matches:
        raise ValueError("No predictions found in expected format 'Event : Time : Confidence'")
    
    for event, time_str, confidence_str in matches:
        event = event.strip()
        try:
            time = float(time_str.strip())
            confidence = int(confidence_str.strip())
            predictions[event] = (time, confidence)
        except ValueError:
            raise ValueError(f"Invalid format for {event}: time={time_str}, confidence={confidence_str}")
    
    # Validate with Pydantic
    validated_predictions = {}
    for event, (time, confidence) in predictions.items():
        pred = Prediction(event=event, time=time, confidence=confidence)
        validated_predictions[pred.event] = (pred.time, pred.confidence)
    
    # Verify events match expected events
    expected_set = set(expected_events)
    predicted_set = set(validated_predictions.keys())
    
    if predicted_set != expected_set:
        missing = expected_set - predicted_set
        extra = predicted_set - expected_set
        error_msg = []
        if missing:
            error_msg.append(f"Missing predictions for: {', '.join(missing)}")
        if extra:
            error_msg.append(f"Unexpected predictions for: {', '.join(extra)}")
        raise ValueError("; ".join(error_msg))
    
    # Return validated Pydantic model
    return PredictedTimes(predictions=validated_predictions)

def predict_missing_times(best_times: Dict[str, float]) -> Dict[str, Tuple[float, int]]:
    """
    Predict missing swim times using OpenAI API.
    
    Args:
        best_times: Dictionary of {event: time_in_seconds} where None values indicate missing times
    
    Returns:
        Dict[str, Tuple[float, int]]: Validated predictions {event: (time_in_seconds, confidence)} for missing events
        where confidence is an integer between 1-5
    
    Raises:
        ValueError: If validation fails (format, events don't match, etc.)
        Exception: If API call fails or parsing fails
    """
    # Get expected events (where best_times[event] is None)
    expected_events = [event for event, time in best_times.items() if time is None]
    
    # If no missing events, return empty dict
    if not expected_events:
        return {}
    
    # Create the prompt using the function
    prompt = format_best_times_prompt(best_times)
    system_prompt = load_system_prompt()
    
    # Retry up to 3 times on validation errors
    max_attempts = 3
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Call OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse and validate predictions
            response_content = response.choices[0].message.content
            validated = parse_predictions_from_text(response_content, expected_events)
            
            # Return the predictions dictionary if successful
            return validated.predictions
            
        except (ValueError, Exception) as e:
            last_error = e
            if attempt < max_attempts:
                # Continue to next attempt
                continue
            else:
                # All attempts exhausted, raise the error
                raise last_error




            
