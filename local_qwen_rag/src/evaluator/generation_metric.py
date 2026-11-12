from rouge_score import rouge_scorer
import nltk
import jieba
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

nltk.download("punkt", quiet=True)
scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"])

def calc_rouge(pred: str, ref: str):
    scores = scorer.score(ref, pred)
    return {
        "rouge1_f": scores["rouge1"].fmeasure,
        "rouge2_f": scores["rouge2"].fmeasure,
        "rougeL_f": scores["rougeL"].fmeasure
    }

def calc_bleu(pred_text, ref_text):
    pred_tokens = list(jieba.cut(pred_text))
    ref_tokens = [list(jieba.cut(ref_text))]
    # 加入平滑，解决4-gram为0直接得分归零
    smooth = SmoothingFunction().method4
    score = sentence_bleu(
        ref_tokens,
        pred_tokens,
        weights=(0.25, 0.25, 0.25, 0.25),
        smoothing_function=smooth
    )
    return round(score, 4)