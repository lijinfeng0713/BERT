python ./t2t_bert/distributed_data_prepare/classification_data_prepare.py \
	--buckets /data/xuht \
	--train_file sentence_embedding/new_data/cluster_corpus_fasttext_train.txt \
	--dev_file sentence_embedding/new_data/cluster_corpus_fasttext_eval.txt \
	--test_file sentence_embedding/new_data/cluster_corpus_fasttext_test.txt \
	--train_result_file sentence_embedding/new_data/data/train_tfrecords \
	--dev_result_file  sentence_embedding/new_data/data/dev_tfrecords\
	--test_result_file  sentence_embedding/new_data/data/test_tfrecords\
	--vocab_file w2v/tencent_ai_lab/char_id.txt \
	--label_id /data/xuht/sentence_embedding/cluster_corpus_label_dict.json \
	--lower_case True \
	--max_length 128 \
	--if_rule "no_rule" \
	--rule_word_dict /data/xuht/porn/rule/rule/phrases.json \
	--rule_word_path /data/xuht/porn/rule/rule/mined_porn_domain_adaptation_v2.txt \
	--rule_label_dict /data/xuht/porn/rule/rule/rule_label_dict.json \
	--with_char "no" \
	--char_len 5 \
	--predefined_vocab_size 50000 \
	--corpus_vocab_path sentence_embedding/new_data/data/char_id.txt \
	--data_type fasttext \
	--tokenizer_type 'jieba'
