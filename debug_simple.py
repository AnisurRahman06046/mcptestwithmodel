import asyncio
from src.services.real_model_manager import real_model_manager

async def test_simple_enhancement():
    # Load model
    real_model_manager.load_model('qwen2.5-1.5b')

    # Direct simple prompt
    query = "products"
    simple_prompt = f"Enhance this e-commerce query: '{query}' - make it more specific for business data:"

    result = real_model_manager.inference(simple_prompt, max_tokens=25, temperature=0.3)

    print("Query:", query)
    print("Enhanced:", result['text'].strip())
    print("Different?", result['text'].strip() != query)

if __name__ == "__main__":
    asyncio.run(test_simple_enhancement())