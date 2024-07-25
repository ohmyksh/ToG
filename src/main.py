import os
import json
import argparse
from tqdm import tqdm
from copy import copy
import logging
from ToG import *
import random

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__) 

def get_args(): 
    parser = argparse.ArgumentParser() 
    parser.add_argument("-c", "--config_path", type=str, required=True)
    args = parser.parse_args()
    config_path = args.config_path
    with open(config_path, "r") as f:
        args = json.load(f)
    args = argparse.Namespace(**args)
    args.config_path = config_path
    return args


def main():
    args = get_args()
    logger.info(f"{args}")

    # output dir
    if os.path.exists(args.output_dir) is False:
        os.makedirs(args.output_dir)
    dir_name = os.listdir(args.output_dir)
    for i in range(10000):
        if str(i) not in dir_name:
            args.output_dir = os.path.join(args.output_dir, str(i))
            os.makedirs(args.output_dir)
            break
    logger.info(f"output dir: {args.output_dir}")
    # save config
    with open(os.path.join(args.output_dir, "config.json"), "w") as f:
        json.dump(args.__dict__, f, indent=4)
    # create output file
    output_file = open(os.path.join(args.output_dir, "output.txt"), "w")

    # load data
    if args.dataset == "CWQ":
        #data = CWQ(args.data_path)
        raise NotImplemented
    elif args.dataset == "WebQSP":
        raise NotImplemented
        #data = WebQSP(args.data_path)
    elif args.dataset == "QALD-10":
        with open('/home/shkim/ToG-implement/data/qald_10-en.json',encoding='utf-8') as f:
            data = json.load(f) 
        topic_entity = "qid_topic_entity"
    else:
        raise NotImplementedError

    # generation method
    if args.method == "IO":
        model = IO_prompt(args)
    elif args.method == "CoT":
        model = CoT_prompt(args)
    elif args.method == "ToG":
        model = ToG(args)
    else:
        raise NotImplementedError
    
    if args.sample != -1:
            samples = min(len(data), args.sample)
            data = random.sample(data, samples)
            
            
    logger.info("start inference")
    for i in tqdm(range(len(data))):
        batch = data[i]
        # measure total time
        # inference_start_time = time.perf_counter()
        pred = model.inference(batch["question"], batch[topic_entity])
        # inference_end_time = time.perf_counter()
        #total_time = (inference_end_time - inference_start_time)
        pred = pred.strip()
        ret = {
            "question": batch["question"],
            "prediction": pred,
            #"tot_time": total_time,
        }
        output_file.write(json.dumps(ret)+"\n")
        print("pred: ", pred)
    
if __name__ == "__main__":
    main()