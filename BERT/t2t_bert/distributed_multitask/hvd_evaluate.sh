python ./t2t_bert/distributed_bin/evaluate_api.py \
 --buckets "/data/xuht" \
 --config_file "./data/textcnn/textcnn.json" \
 --init_checkpoint "multi_task/model/" \
 --vocab_file "./data/multi_cased_L-12_H-768_A-12/vocab.txt" \
 --label_id "./data/lazada_multilingual/label_dict.json" \
 --max_length 128 \
 --train_file "" \
 --dev_file "" \
 --model_output "multi_task/" \
 --epoch 20 \
 --num_classes 4 \
 --train_size  1825708\
 --eval_size 100000 \
 --batch_size 32 \
 --model_type "bert" \
 --if_shard 0 \
 --is_debug 1 \
 --run_type "sess" \
 --opt_type "hvd" \
 --num_gpus 4 \
 --parse_type "parse_batch" \
 --rule_model "normal" \
 --profiler "no" \
 --train_op "adam" \
 --running_type "train" \
 --cross_tower_ops_type "paisoar" \
 --distribution_strategy "MirroredStrategy" \
 --load_pretrained "no" \
 --w2v_path "multi_cased_L-12_H-768_A-12/vocab_w2v.txt" \
 --with_char "no_char" \
 --input_target "a" \
 --decay "no" \
 --warmup "no" \
 --distillation "normal" \
 --temperature 2.0 \
 --distillation_ratio 0.5 \
 --task_type "single_sentence_classification" \
 --classifier order_classifier \
 --mode "multi_task" \
 --multi_task_type "lcqmc" \
 --multi_task_config "./t2t_bert/distributed_multitask/multi_task_eval_local.json"


