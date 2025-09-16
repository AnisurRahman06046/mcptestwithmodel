import asyncio
from src.services.real_model_manager import real_model_manager

async def debug_enhancement():
    # Load model
    success = real_model_manager.load_model('qwen2.5-1.5b')
    print(f"Model loaded: {success}")

    # Simple enhancement prompt
    query = "products"
    prompt = f"""Transform this e-commerce query to be more specific:

Original: "{query}"

Make it more detailed and specific for inventory data. Add business context.

Enhanced:"""

    result = real_model_manager.inference(prompt, max_tokens=30, temperature=0.3)
    raw_output = result['text']

    print(f"Original query: '{query}'")
    print(f"Raw AI output: '{raw_output}'")
    print(f"Output repr: {repr(raw_output)}")

    # Simple processing
    enhanced = raw_output.strip()

    # Remove quotes
    if enhanced.startswith('"') and enhanced.endswith('"'):
        enhanced = enhanced[1:-1]

    print(f"Processed output: '{enhanced}'")
    print(f"Different from original: {enhanced != query}")

if __name__ == "__main__":
    asyncio.run(debug_enhancement())