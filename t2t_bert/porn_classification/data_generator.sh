python data_processor.py \
	--train_file /data/xuht/porn/seqing_train_20180821 \
	--test_file /data/xuht/porn/seqing_test_20180821 \
	--train_result_file /data/xuht/porn/seqing_train_20180821_tf_records \
	--test_result_file  /data/xuht/porn/seqing_test_20180821_tf_records\
	--vocab_file /data/xuht/chinese_L-12_H-768_A-12/vocab.txt \
	--label_id /data/xuht/porn/label_dict.json \
	--lower_case True \
	--max_length 128 \
