import tensorflow as tf
import numpy as np
import json
from bunch import Bunch
import os, sys

def model_config_parser(FLAGS):

	print(FLAGS.model_type)

	if FLAGS.model_type in ["bert", "bert_rule"]:
		config = json.load(open(FLAGS.config_file, "r"))
		config = Bunch(config)
		config.use_one_hot_embeddings = True
		config.scope = "bert"
		config.dropout_prob = 0.1
		config.label_type = "single_label"
		config.model_type = FLAGS.model_type
		config.init_lr = 2e-5
		config.loss = "entropy"
		config.rule_type_size = 2
		if FLAGS.task_type in ["pair_sentence_classification"]:
			config.classifier = FLAGS.classifier

	elif FLAGS.model_type in ["bert_small"]:
		config = json.load(open(FLAGS.config_file, "r"))
		config = Bunch(config)
		config.use_one_hot_embeddings = True
		config.scope = "bert"
		config.dropout_prob = 0.1
		config.label_type = "single_label"
		config.model_type = FLAGS.model_type
		config.init_lr = 2e-5
		config.num_hidden_layers = FLAGS.num_hidden_layers
		config.loss = "entropy"
		config.rule_type_size = 2
		if FLAGS.task_type in ["pair_sentence_classification"]:
			config.classifier = FLAGS.classifier
			config.output_layer = FLAGS.output_layer

	elif FLAGS.model_type in ["textcnn", 'textcnn_distillation']:
		from data_generator import load_w2v
		w2v_path = os.path.join(FLAGS.buckets, FLAGS.w2v_path)
		vocab_path = os.path.join(FLAGS.buckets, FLAGS.vocab_file)

		print(w2v_path, vocab_path)

		[w2v_embed, token2id, 
		id2token, is_extral_symbol] = load_w2v.load_pretrained_w2v(vocab_path, w2v_path)
		config = json.load(open(FLAGS.config_file, "r"))
		config = Bunch(config)
		config.token_emb_mat = w2v_embed
		config.char_emb_mat = None
		config.vocab_size = w2v_embed.shape[0]
		config.max_length = FLAGS.max_length
		config.emb_size = w2v_embed.shape[1]
		config.scope = "textcnn"
		config.char_dim = w2v_embed.shape[1]
		config.char_vocab_size = w2v_embed.shape[0]
		config.char_embedding = None
		config.model_type = FLAGS.model_type
		config.dropout_prob = config.dropout_rate
		config.init_lr = config.learning_rate
		if is_extral_symbol == 1:
			config.extra_symbol = ["<pad>", "<unk>", "<s>", "</s>"]
			print("==need extra_symbol==")

		if FLAGS.task_type in ["pair_sentence_classification"]:
			config.classifier = FLAGS.classifier
			config.output_layer = FLAGS.output_layer

	elif FLAGS.model_type in ["textlstm", "textlstm_distillation"]:
		from data_generator import load_w2v
		w2v_path = os.path.join(FLAGS.buckets, FLAGS.w2v_path)
		vocab_path = os.path.join(FLAGS.buckets, FLAGS.vocab_file)

		print(w2v_path, vocab_path)

		[w2v_embed, token2id, 
		id2token, is_extral_symbol] = load_w2v.load_pretrained_w2v(vocab_path, w2v_path)
		config = json.load(open(FLAGS.config_file, "r"))
		config = Bunch(config)
		config.token_emb_mat = w2v_embed
		config.char_emb_mat = None
		config.vocab_size = w2v_embed.shape[0]
		config.max_length = FLAGS.max_length
		config.emb_size = w2v_embed.shape[1]
		config.scope = "textlstm"
		config.char_dim = w2v_embed.shape[1]
		config.char_vocab_size = w2v_embed.shape[0]
		config.char_embedding = None
		config.model_type = FLAGS.model_type
		config.dropout_prob = config.dropout_rate
		config.init_lr = config.learning_rate
		config.grad_clip = "gloabl_norm"
		config.clip_norm = 5.0
		if is_extral_symbol == 1:
			config.extra_symbol = ["<pad>", "<unk>", "<s>", "</s>"]
			print("==need extra_symbol==")
		
		if FLAGS.task_type in ["pair_sentence_classification"]:
			config.classifier = FLAGS.classifier
			config.output_layer = FLAGS.output_layer

	elif FLAGS.model_type in ["match_pyramid", "match_pyramid_distillation"]:
		from data_generator import load_w2v
		w2v_path = os.path.join(FLAGS.buckets, FLAGS.w2v_path)
		vocab_path = os.path.join(FLAGS.buckets, FLAGS.vocab_file)

		print(w2v_path, vocab_path)

		[w2v_embed, token2id, 
		id2token, is_extral_symbol] = load_w2v.load_pretrained_w2v(vocab_path, w2v_path)
		config = json.load(open(FLAGS.config_file, "r"))
		config = Bunch(config)
		config.token_emb_mat = w2v_embed
		config.char_emb_mat = None
		config.vocab_size = w2v_embed.shape[0]
		config.max_length = FLAGS.max_length
		config.emb_size = w2v_embed.shape[1]
		config.scope = "match_pyramid"
		config.char_dim = w2v_embed.shape[1]
		config.char_vocab_size = w2v_embed.shape[0]
		config.char_embedding = None
		config.model_type = FLAGS.model_type
		config.dropout_prob = config.dropout_rate
		config.init_lr = config.learning_rate
		config.grad_clip = "gloabl_norm"
		config.clip_norm = 5.0
		if is_extral_symbol == 1:
			config.extra_symbol = ["<pad>", "<unk>", "<s>", "</s>"]
			print("==need extra_symbol==")
		config.max_seq_len = FLAGS.max_length
		if FLAGS.task_type in ["interaction_pair_sentence_classification"]:
			config.classifier = FLAGS.classifier
			config.output_layer = FLAGS.output_layer

		if config.compress_emb:
			config.embedding_dim_compressed = config.cnn_num_filters

	return config