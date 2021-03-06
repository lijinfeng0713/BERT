python ./t2t_bert/distributed_bin/tf_serving_api.py \
	--buckets "/data/xuht" \
	--vocab "lcqmc/data/distillation/char_id.txt" \
	--do_lower_case True \
	--url "30.8.113.58" \
	--port "7901" \
	--model_name "match_pyramid" \
	--signature_name "serving_default" \
	--versions "1552980867" \
	--task_type "pair_sentence_classification" \
	--tokenizer "jieba_char" \
	--with_char "no_char" \
	--output_path "lcqmc/data/match_pyramid_result.json" \
	--input_data "lcqmc/data/match_pyramid_test.json" \
	--model_type "interaction" \
	--max_seq_length 64
