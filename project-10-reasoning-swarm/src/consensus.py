import numpy as np
from openai import AsyncOpenAI
from src.config import settings
from src.models import Round

_DEFAULT_SCORE = 0.5


async def compute_agreement_score(rnd: Round) -> float:
    """
    Cosine similarity between proposer and critic key-claim embeddings.
    High similarity means agents are converging -- consensus is near.
    """
    proposer_claims: list[str] = []
    critic_claims: list[str] = []

    for turn in rnd.turns:
        if turn.agent == "proposer":
            proposer_claims.extend(turn.key_claims)
        elif turn.agent == "critic":
            critic_claims.extend(turn.key_claims)

    if not proposer_claims or not critic_claims:
        return _DEFAULT_SCORE

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    texts = proposer_claims + critic_claims
    response = await client.embeddings.create(model=settings.embedding_model, input=texts)
    embeddings = np.array([r.embedding for r in response.data])

    p_embs = embeddings[: len(proposer_claims)]
    c_embs = embeddings[len(proposer_claims) :]

    scores = []
    for pe in p_embs:
        for ce in c_embs:
            cos_sim = float(np.dot(pe, ce) / (np.linalg.norm(pe) * np.linalg.norm(ce)))
            scores.append(cos_sim)

    return float(np.mean(scores)) if scores else _DEFAULT_SCORE
