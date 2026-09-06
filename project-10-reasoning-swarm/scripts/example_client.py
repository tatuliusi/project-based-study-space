"""
Quick example showing how to run a debate and stream the result.

Usage:
    python scripts/example_client.py
"""
import asyncio
import httpx

BASE = "http://localhost:8000"


async def run_debate(question: str, domain: str = "general") -> None:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BASE}/debates",
            json={"question": question, "domain": domain, "max_rounds": 2},
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"Debate ID  : {data['debate_id']}")
        print(f"Rounds     : {data['rounds_completed']}")
        print(f"Consensus  : {data['consensus_reached']}")
        print(f"Confidence : {data['consensus_confidence']}")

        detail = await client.get(f"{BASE}/debates/{data['debate_id']}/consensus")
        detail.raise_for_status()
        print(f"\nAnswer: {detail.json()['answer']}")


if __name__ == "__main__":
    asyncio.run(run_debate("Is consciousness reducible to physical brain states?", "philosophy"))
