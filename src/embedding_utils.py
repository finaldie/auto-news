########################################################################
# Embedding Utils
########################################################################
import numpy as np


def similarity_topk(embedding_items: list, metric_type, threshold=None, k=3):
    """
    @param embedding_items [{item_id, distance}, ...]
    @param metric_type L2, IP, COSINE
    @threshold to filter the result
    @k max number of returns
    """
    if metric_type == "L2":
        return similarity_topk_l2(embedding_items, threshold, k)
    elif metric_type in ("IP", "COSINE"):
        # assume IP type all embeddings has been normalized
        return similarity_topk_cosine(embedding_items, threshold, k)
    else:
        raise Exception(f"Unknown metric_type: {metric_type}")


def similarity_topk_l2(items: list, threshold, k):
    """
    metric_type L2, the value range [0, +inf)
    * The smaller (Close to 0), the more similiar
    * The larger, the less similar

    so, we will filter in distance <= threshold first, then get top-k
    """
    valid_items = items

    if threshold is not None:
        valid_items = [x for x in items if x["distance"] <= threshold]

    # sort in ASC
    sorted_items = sorted(
        valid_items,
        key=lambda item: item["distance"],
    )

    # The returned value is sorted by most similar -> least similar
    return sorted_items[:k]


def similarity_topk_cosine(items: list, threshold, k):
    """
    metric_type IP (normalized) or COSINE, the value range [-1, 1]
    * 1 indicates that the vectors are identical in direction.
    * 0 indicates orthogonality (no similarity in direction).
    * -1 indicates that the vectors are opposite in direction.

    so, we will filter in distance >= threshold first, then get top-k
    """
    valid_items = items

    if threshold is not None:
        valid_items = [x for x in items if x["distance"] >= threshold]

    # sort in DESC
    sorted_items = sorted(
        valid_items,
        key=lambda item: item["distance"],
        reverse=True,
    )

    # The returned value is sorted by most similar -> least similar
    return sorted_items[:k]


def l2_norm(emb):
    return (np.array(emb) / np.linalg.norm(emb)).tolist()
