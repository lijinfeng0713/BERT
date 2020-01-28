nohup python ./run_pretraining.py \
	--bert_config_file "" \
	--input_file "gs://yyht_source/pretrain/data_single/chunk_0.tfrecords,gs://yyht_source/pretrain/data_single/chunk_1.tfrecords,gs://yyht_source/pretrain/data_single/chunk_2.tfrecords,gs://yyht_source/pretrain/data_single/chunk_3.tfrecords,gs://yyht_source/pretrain/data_single/chunk_4.tfrecords,gs://yyht_source/pretrain/data_single/chunk_5.tfrecords,gs://yyht_source/pretrain/data_single/chunk_6.tfrecords,gs://yyht_source/pretrain/data_single/chunk_7.tfrecords,gs://yyht_source/pretrain/data_single/chunk_8.tfrecords,gs://yyht_source/pretrain/data_single/chunk_9.tfrecords,gs://yyht_source/pretrain/data_single/chunk_10.tfrecords,gs://yyht_source/pretrain/data_single/chunk_11.tfrecords,gs://yyht_source/pretrain/data_single/chunk_12.tfrecords,gs://yyht_source/pretrain/data_single/chunk_13.tfrecords,gs://yyht_source/pretrain/data_single/chunk_14.tfrecords,gs://yyht_source/pretrain/data_single/chunk_15.tfrecords,gs://yyht_source/pretrain/data_single/chunk_16.tfrecords,gs://yyht_source/pretrain/data_single/chunk_17.tfrecords" \
	--output_dir "gs://yyht_source/pretrain/model/brightmart_albert_zh" \
	--max_seq_length 512 \
	--max_predictions_per_seq 78 \
	--do_train True \
	--train_batch_size 1024 \
	--learning_rate 1e-4 \
	--num_train_steps 150000 \
	--num_warmup_steps 15000 \
	--save_checkpoints_steps 1000 \
	--iterations_per_loop 1000 \
	--use_tpu True \
	--tpu_name htxu91 \
	--num_tpu_cores 8
