from data import CWQ, WebQSP, QALD
from tqdm import tqdm
import logging
import os
import json
import argparse
import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=str, required=True)
    tmp = parser.parse_args()
    with open(os.path.join(tmp.dir, "config.json"), "r") as f:
        args = json.load(f)
    args = argparse.Namespace(**args)
    args.output_dir = tmp.dir
    return args

# import sys
# import json
# Webqsp eval.py
# def FindInList(entry,elist):
#     for item in elist:
#         if entry == item:
#             return True
#     return False
            
# def CalculatePRF1(goldAnswerList, predAnswerList):
#     if len(goldAnswerList) == 0:
#         if len(predAnswerList) == 0:
#             return [1.0, 1.0, 1.0]  # consider it 'correct' when there is no labeled answer, and also no predicted answer
#         else:
#             return [0.0, 1.0, 0.0]  # precision=0 and recall=1 when there is no labeled answer, but has some predicted answer(s)
#     elif len(predAnswerList)==0:
#         return [1.0, 0.0, 0.0]    # precision=1 and recall=0 when there is labeled answer(s), but no predicted answer
#     else:
#         glist =[x["AnswerArgument"] for x in goldAnswerList]
#         plist =predAnswerList

#         tp = 1e-40  # numerical trick
#         fp = 0.0
#         fn = 0.0

#         for gentry in glist:
#             if FindInList(gentry,plist):
#                 tp += 1
#             else:
#                 fn += 1
#         for pentry in plist:
#             if not FindInList(pentry,glist):
#                 fp += 1


#         precision = tp/(tp + fp)
#         recall = tp/(tp + fn)
        
#         f1 = (2*precision*recall)/(precision+recall)
#         return [precision, recall, f1]


# def main():
#     if len(sys.argv) != 3:
#         print "Usage: python eval.py goldData predAnswers"
#         sys.exit(-1)

#     goldData = json.loads(open(sys.argv[1]).read())
#     predAnswers = json.loads(open(sys.argv[2]).read())

#     PredAnswersById = {}

#     for item in predAnswers:
#         PredAnswersById[item["QuestionId"]] = item["Answers"]

#     total = 0.0
#     f1sum = 0.0
#     recSum = 0.0
#     precSum = 0.0
#     numCorrect = 0
#     for entry in goldData["Questions"]:

#         skip = True
#         for pidx in range(0,len(entry["Parses"])):
#             np = entry["Parses"][pidx]
#             if np["AnnotatorComment"]["QuestionQuality"] == "Good" and np["AnnotatorComment"]["ParseQuality"] == "Complete":
#                 skip = False

#         if(len(entry["Parses"])==0 or skip):
#             continue

#         total += 1
    
#         id = entry["QuestionId"]
    
#         if id not in PredAnswersById:
#             print "The problem " + id + " is not in the prediction set"
#             print "Continue to evaluate the other entries"
#             continue

#         if len(entry["Parses"]) == 0:
#             print "Empty parses in the gold set. Breaking!!"
#             break

#         predAnswers = PredAnswersById[id]

#         bestf1 = -9999
#         bestf1Rec = -9999
#         bestf1Prec = -9999
#         for pidx in range(0,len(entry["Parses"])):
#             pidxAnswers = entry["Parses"][pidx]["Answers"]
#             prec,rec,f1 = CalculatePRF1(pidxAnswers,predAnswers)
#             if f1 > bestf1:
#                 bestf1 = f1
#                 bestf1Rec = rec
#                 bestf1Prec = prec

#         f1sum += bestf1
#         recSum += bestf1Rec
#         precSum += bestf1Prec
#         if bestf1 == 1.0:
#             numCorrect += 1

#     print "Number of questions:", int(total)
#     print "Average precision over questions: %.3f" % (precSum / total)
#     print "Average recall over questions: %.3f" % (recSum / total)
#     print "Average f1 over questions (accuracy): %.3f" % (f1sum / total)
#     print "F1 of average recall and average precision: %.3f" % (2 * (recSum / total) * (precSum / total) / (recSum / total + precSum / total))
#     print "True accuracy (ratio of questions answered exactly correctly): %.3f" % (numCorrect / total)


def main():
    args = get_args()
    logger.info(f"{args}")
    
    if args.dataset == 'CWQ':
        data = CWQ(args.data_path)
    elif args.dataset == 'WebQSP':
        data = WebQSP(args.data_path)
    elif args.dataset == 'QALD':
        data = QALD(args.data_path)
    else:
        raise NotImplementedError
    data.format(fewshot=args.fewshot)
    
    
    dataset = {}
    for i in range(len(data.dataset)):
        t = data.dataset[i]
        dataset[t["question"]] = [
            t["answer"], 
        ]
        
    metrics = ["EM", "F1", "Precision", "Recall"]
    value = [[] for _ in range(len(metrics))]
    with open(os.path.join(args.output_dir, "output.txt"), "r") as fin:
        lines = fin.readlines()
    pred_out = open(f"{args.output_dir}/details.txt", "w")
    for line in tqdm(lines):
        rd = json.loads(line)
        qid = rd["qid"]
        pred = rd["prediction"]
        ground_truth, ground_truth_id, case = dataset[qid]
        
        # pred = data.get_real_prediction(pred)

        em_ret = data.exact_match_score(
            pred, 
            ground_truth, 
            ground_truth_id
        )
        f1_ret = data.f1_score(
            pred, 
            ground_truth, 
            ground_truth_id
        )
        value[0].append(em_ret["correct"])
        for i, k in enumerate(f1_ret.keys()):
            value[i+1].append(f1_ret[k])

        detail = {
            "qid": qid, 
            "final_pred": pred,
            "EM": str(em_ret["correct"]), 
            "F1": str(f1_ret["f1"]) 
        }
        pred_out.write(json.dumps(detail)+"\n")

    ret = []
    for i, metric in enumerate(metrics):
        val = np.array(value[i])
        ret.append([metric, val.mean()])
    df = pd.DataFrame(ret)
    df.to_csv(f"{args.output_dir}/result.tsv", index=False, header=False)


if __name__ == "__main__":
    main()