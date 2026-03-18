# Retrieval Fixture Benchmark

## Aggregate

| Engine | Budget | Queries | Precision | Recall | Anchor recall | Surface bundle | False positives | Tokens to first correct | Tokens to full set | Full change set | Paired top | Top-1 | Top-K | Caller | Trace | No-answer | Avg context tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DeCodifier | 2000 | 18 | 58% | 100% | 100% | 100% | 0% | 102.69 | 213.80 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 170.17 |
| DeCodifier | 1000 | 18 | 58% | 100% | 100% | 100% | 0% | 102.69 | 213.80 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 170.17 |
| DeCodifier | 500 | 18 | 58% | 100% | 100% | 100% | 0% | 102.69 | 213.80 | 100% | 100% | 100% | 100% | 100% | 100% | 100% | 170.17 |
| Lexical Baseline | 2000 | 18 | 28% | 62% | 65% | 0% | 44% | 76.80 | 232 | 20% | 0% | 39% | 33% | 0% | 0% | 0% | 223.61 |
| Lexical Baseline | 1000 | 18 | 28% | 62% | 65% | 0% | 44% | 76.80 | 232 | 20% | 0% | 39% | 33% | 0% | 0% | 0% | 223.61 |
| Lexical Baseline | 500 | 18 | 28% | 62% | 65% | 0% | 44% | 76.80 | 232 | 20% | 0% | 39% | 33% | 0% | 0% | 0% | 223.61 |
| Embedding Baseline | 2000 | 18 | 36% | 69% | 85% | 0% | 28% | 124.69 | 282 | 20% | 0% | 22% | 22% | 0% | 0% | 0% | 206.33 |
| Embedding Baseline | 1000 | 18 | 36% | 69% | 85% | 0% | 28% | 124.69 | 282 | 20% | 0% | 22% | 22% | 0% | 0% | 0% | 206.33 |
| Embedding Baseline | 500 | 18 | 36% | 69% | 85% | 0% | 28% | 124.69 | 282 | 20% | 0% | 22% | 22% | 0% | 0% | 0% | 206.33 |

## DeCodifier (2000 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | correct |
| permission check | correct | correct | correct |
| session expiration | correct | correct | ignored |
| refresh token | correct | correct | ignored |
| login trace | correct | correct | correct |
| noise decoys | ignored | ignored | ignored |

## DeCodifier (1000 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | correct |
| permission check | correct | correct | correct |
| session expiration | correct | correct | ignored |
| refresh token | correct | correct | ignored |
| login trace | correct | correct | correct |
| noise decoys | ignored | ignored | ignored |

## DeCodifier (500 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | correct |
| permission check | correct | correct | correct |
| session expiration | correct | correct | ignored |
| refresh token | correct | correct | ignored |
| login trace | correct | correct | correct |
| noise decoys | ignored | ignored | ignored |

## Lexical Baseline (2000 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | miss |
| permission check | miss | hit@1 | miss |
| session expiration | correct | correct | false_positive |
| refresh token | correct | correct | false_positive |
| login trace | hit@2 | hit@1 | hit@1 |
| noise decoys | false_positive | false_positive | false_positive |

## Lexical Baseline (1000 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | miss |
| permission check | miss | hit@1 | miss |
| session expiration | correct | correct | false_positive |
| refresh token | correct | correct | false_positive |
| login trace | hit@2 | hit@1 | hit@1 |
| noise decoys | false_positive | false_positive | false_positive |

## Lexical Baseline (500 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | miss |
| permission check | miss | hit@1 | miss |
| session expiration | correct | correct | false_positive |
| refresh token | correct | correct | false_positive |
| login trace | hit@2 | hit@1 | hit@1 |
| noise decoys | false_positive | false_positive | false_positive |

## Embedding Baseline (2000 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | correct |
| permission check | hit@3 | hit@2 | hit@2 |
| session expiration | correct | hit@2 | false_positive |
| refresh token | hit@2 | hit@2 | false_positive |
| login trace | hit@2 | hit@3 | hit@1 |
| noise decoys | false_positive | false_positive | false_positive |

## Embedding Baseline (1000 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | correct |
| permission check | hit@3 | hit@2 | hit@2 |
| session expiration | correct | hit@2 | false_positive |
| refresh token | hit@2 | hit@2 | false_positive |
| login trace | hit@2 | hit@3 | hit@1 |
| noise decoys | false_positive | false_positive | false_positive |

## Embedding Baseline (500 tokens)

| Query | harbor_api | atlas_workspace | fastapi_full_stack_backend |
| --- | --- | --- | --- |
| token validation | correct | correct | correct |
| permission check | hit@3 | hit@2 | hit@2 |
| session expiration | correct | hit@2 | false_positive |
| refresh token | hit@2 | hit@2 | false_positive |
| login trace | hit@2 | hit@3 | hit@1 |
| noise decoys | false_positive | false_positive | false_positive |
