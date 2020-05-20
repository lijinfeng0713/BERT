import tensorflow as tf
import numpy as np
from utils.bert import bert_modules
from utils.textcnn import textcnn_utils, dgcnn_utils
from utils.bimpm import match_utils
from utils.embed import integration_func
from model.base_classify import base_model
from utils.qanet import qanet_layers
from utils.qanet.qanet_layers import highway
from utils.dsmm.tf_common.nn_module import encode, attend, mlp_layer
from utils.bert import bert_utils
from utils.esim import esim_utils

class TextCNN(base_model.BaseModel):
	def __init__(self, config):
		super(TextCNN, self).__init__(config)

	def build_encoder(self, input_ids, input_char_ids, is_training, **kargs):
		reuse = kargs["reuse"]
		if is_training:
			dropout_rate = self.config.dropout_rate
		else:
			dropout_rate = 0.0
		# dropout_rate = tf.cond(is_training, 
		# 					lambda:self.config.dropout_rate,
		# 					lambda:0.0)

		word_emb_dropout = tf.nn.dropout(self.word_emb, 1)
		with tf.variable_scope(self.config.scope+"_input_highway", reuse=reuse):
			input_dim = word_emb_dropout.get_shape()[-1]
			if self.config.get("highway", "dense_highway") == "dense_highway":
				tf.logging.info("***** dense highway *****")
				sent_repres = match_utils.multi_highway_layer(word_emb_dropout, input_dim, self.config.highway_layer_num)
			elif self.config.get("highway", "dense_highway") == "conv_highway":
				tf.logging.info("***** conv highway *****")
				sent_repres = highway(word_emb_dropout, 
								size = self.config.num_filters, 
								scope = "highway", 
								dropout = dropout_rate, 
								reuse = reuse)
			else:
				sent_repres = word_emb_dropout

		input_mask = tf.cast(input_ids, tf.bool)
		input_len = tf.reduce_sum(tf.cast(input_mask, tf.int32), -1)

		mask = tf.expand_dims(input_mask, -1)
		sent_repres *= tf.cast(mask, tf.float32)

		with tf.variable_scope(self.config.scope+"_encoder", reuse=reuse):
			if kargs.get("cnn_type", 'textcnn') == 'textcnn':
				self.output = textcnn_utils.text_cnn_v1(sent_repres, 
						self.config.get("filter_size", [1,3,5]), 
						"textcnn", 
						sent_repres.get_shape()[-1], 
						self.config.num_filters, 
						max_pool_size=self.config.max_pool_size,
						input_mask=input_mask)
				self.sequence_output = None
				tf.logging.info("***** normal cnn *****")
			elif kargs.get("cnn_type", 'textcnn') == 'multilayer_textcnn':
				self.output = textcnn_utils.cnn_multiple_layers(sent_repres, 
					self.config.get("filter_size", [1,3,5]), 
					"textcnn", 
					sent_repres.get_shape()[-1],
					self.config.num_filters,
					max_pool_size=2,
					input_mask=input_mask, 
					is_training_flag=is_training)
				self.sequence_output = None
				tf.logging.info("***** multi-layer cnn *****")
			elif kargs.get("cnn_type", 'textcnn') == 'gated_cnn':
				input_shape = bert_utils.get_shape_list(sent_repres, expected_rank=3)
				hidden_size = self.config['cnn_num_filters']
				input_width = input_shape[-1]
				if input_width != hidden_size and self.config['cnn_residual']:
					sent_repres = tf.layers.dense(
						sent_repres,
						hidden_size,
						use_bias=None,
						activation=None,
						kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
					tf.logging.info("==apply embedding linear projection==")

				self.sequence_output = encode(sent_repres, 
											method=self.config["encode_method"],
											 input_dim=input_dim,
											 params=self.config,
											 sequence_length=input_len,
											 mask_zero=self.config["embedding_mask_zero"],
											 scope_name=self.scope + "enc_seq", 
											 reuse=tf.AUTO_REUSE,
											 training=is_training)
				print(self.sequence_output.get_shape(), '=====sequence_output shape=====')
				pooled_output = []
				for pooling_method in self.config['pooling_method']:
					if pooling_method == 'avg':
						seq_mask = tf.cast(mask, tf.float32)
						avg_repres = tf.reduce_sum(self.sequence_output*seq_mask, axis=1)/(1e-10+tf.reduce_sum(seq_mask, axis=1))
						pooled_output.append(avg_repres)
						tf.logging.info("***** avg pooling *****")
					elif pooling_method == 'max':
						seq_mask = tf.cast(mask, tf.float32)
						max_avg = tf.reduce_max(qanet_layers.mask_logits(self.sequence_output, seq_mask), axis=1)
						pooled_output.append(max_avg)
						tf.logging.info("***** max pooling *****")
				self.output = tf.concat(pooled_output, axis=-1)
				tf.logging.info("***** seq-encoder *****")
			elif kargs.get("cnn_type", 'textcnn') == 'multilayer_gatedcnn':
				input_shape = bert_utils.get_shape_list(sent_repres, expected_rank=3)
				hidden_size = self.config['cnn_num_filters']
				input_width = input_shape[-1]
				if input_width != hidden_size and self.config['cnn_residual']:
					sent_repres = tf.layers.dense(
						sent_repres,
						hidden_size,
						use_bias=None,
						activation=None,
						kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
					tf.logging.info("==apply embedding linear projection==")

				self.sequence_output = textcnn_utils.gated_cnn(sent_repres, 
												input_mask,
												num_layers=self.config['cnn_num_layers'], 
												num_filters=self.config['cnn_num_filters'], 
												filter_sizes=self.config['cnn_filter_sizes'], 
												bn=self.config['bn'], 
												training=is_training,
												timedistributed=False, 
												scope_name="textcnn", 
												reuse=False, 
												activation=tf.nn.relu,
												gated_conv=self.config['cnn_gated_conv'], 
												residual=self.config['cnn_residual'])
				print(self.sequence_output.get_shape(), '=====sequence_output shape=====')
				pooled_output = []
				for pooling_method in self.config['pooling_method']:
					if pooling_method == 'avg':
						seq_mask = tf.cast(mask, tf.float32)
						avg_repres = tf.reduce_sum(self.sequence_output*seq_mask, axis=1)/(1e-10+tf.reduce_sum(seq_mask, axis=1))
						pooled_output.append(avg_repres)
						tf.logging.info("***** avg pooling *****")
					elif pooling_method == 'max':
						seq_mask = tf.cast(mask, tf.float32)
						max_avg = tf.reduce_max(qanet_layers.mask_logits(self.sequence_output, seq_mask), axis=1)
						pooled_output.append(max_avg)
						tf.logging.info("***** max pooling *****")
				self.output = tf.concat(pooled_output, axis=-1)
				tf.logging.info("***** seq-encoder *****")
			elif kargs.get("cnn_type", 'textcnn') == 'multilayer_resnetcnn':
				input_shape = bert_utils.get_shape_list(sent_repres, expected_rank=3)
				hidden_size = self.config['cnn_num_filters']
				input_width = input_shape[-1]
				if input_width != hidden_size and self.config['cnn_residual']:
					sent_repres = tf.layers.dense(
						sent_repres,
						hidden_size,
						use_bias=None,
						activation=None,
						kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
					tf.logging.info("==apply embedding linear projection==")

				self.sequence_output = textcnn_utils.resnet_cnn(sent_repres,
												input_mask, 
												num_layers=self.config['cnn_num_layers'], 
												num_filters=self.config['cnn_num_filters'], 
												filter_sizes=self.config['cnn_filter_sizes'], 
												bn=self.config['bn'], 
												training=is_training,
												timedistributed=False, 
												scope_name="textcnn", 
												reuse=False, 
												activation=tf.nn.relu,
												gated_conv=self.config['cnn_gated_conv'], 
												residual=self.config['cnn_residual'])
				print(self.sequence_output.get_shape(), '=====sequence_output shape=====')
				pooled_output = []
				for pooling_method in self.config['pooling_method']:
					if pooling_method == 'avg':
						seq_mask = tf.cast(mask, tf.float32)
						avg_repres = tf.reduce_sum(self.sequence_output*seq_mask, axis=1)/(1e-10+tf.reduce_sum(seq_mask, axis=1))
						pooled_output.append(avg_repres)
						tf.logging.info("***** avg pooling *****")
					elif pooling_method == 'max':
						seq_mask = tf.cast(mask, tf.float32)
						max_avg = tf.reduce_max(qanet_layers.mask_logits(self.sequence_output, seq_mask), axis=1)
						pooled_output.append(max_avg)
						tf.logging.info("***** max pooling *****")
				self.output = tf.concat(pooled_output, axis=-1)
				tf.logging.info("***** seq-encoder *****")
			elif kargs.get("cnn_type", 'textcnn') == 'dgcnn':
				input_shape = bert_utils.get_shape_list(sent_repres, expected_rank=3)
				hidden_size = self.config['cnn_num_filters'][0]
				input_width = input_shape[-1]
				# if input_width != hidden_size:
				# 	sent_repres = tf.layers.dense(
				# 		sent_repres,
				# 		hidden_size,
				# 		use_bias=None,
				# 		activation=None,
				# 		kernel_initializer=tf.truncated_normal_initializer(stddev=0.01))
				# 	tf.logging.info("==apply embedding linear projection==")

				self.sequence_output = dgcnn_utils.dgcnn(
												sent_repres, 
												input_mask,
												num_layers=self.config['cnn_num_layers'], 
												dilation_rates=self.config.get('cnn_dilation_rates', [1,2]),
												strides=self.config.get('cnn_dilation_rates', [1,1]),
												num_filters=self.config.get('cnn_num_filters', [128,128]), 
												kernel_sizes=self.config.get('cnn_filter_sizes', [3,3]), 
												is_training=is_training,
												scope_name="textcnn", 
												reuse=False, 
												activation=tf.nn.relu,
												is_casual=self.config['is_casual'],
												padding=self.config.get('padding', 'same')
												)

				print(self.sequence_output.get_shape(), '=====sequence_output shape=====')
				print(mask.get_shape(), "===mask shape===")
				pooled_output = []
				for pooling_method in self.config['pooling_method']:
					if pooling_method == 'avg':
						seq_mask = tf.cast(mask, tf.float32)
						print(tf.reduce_sum(seq_mask, axis=1).get_shape(), "==avg seq shape")
						avg_repres = tf.reduce_sum(self.sequence_output*seq_mask, axis=1)/(1e-10+tf.reduce_sum(seq_mask, axis=1))
						pooled_output.append(avg_repres)
						tf.logging.info("***** avg pooling *****")
					elif pooling_method == 'max':
						seq_mask = tf.cast(mask, tf.float32)
						max_avg = tf.reduce_max(qanet_layers.mask_logits(self.sequence_output, seq_mask), axis=1)
						pooled_output.append(max_avg)
						tf.logging.info("***** max pooling *****")
					elif pooling_method == "last":
						last = esim_utils.last_relevant_output(self.sequence_output, input_len)
						pooled_output.append(last)
						tf.logging.info("***** last pooling *****")
				self.output = tf.concat(pooled_output, axis=-1)
				tf.logging.info("***** seq-encoder *****")
			else:
				self.sequence_output = None
				self.output = textcnn_utils.text_cnn_v1(sent_repres, 
						self.config.get("filter_size", [1,3,5]), 
						"textcnn", 
						sent_repres.get_shape()[-1], 
						self.config.num_filters, 
						max_pool_size=self.config.max_pool_size,
						input_mask=input_mask)
				tf.logging.info("***** normal cnn *****")
			print("output shape====", self.output.get_shape())

	def build_output_logits(self, **kargs):
		input_tensor = self.sequence_output
		input_shape_list = bert_utils.get_shape_list(self.sequence_output, expected_rank=3)
		batch_size = input_shape_list[0]
		seq_length = input_shape_list[1]
		hidden_dims = input_shape_list[2]

		embedding_projection = kargs.get('embedding_projection', None)

		scope = kargs.get('scope', None)
		if scope:
			scope = scope + '/' + 'cls/predictions'
		else:
			scope = 'cls/predictions'

		tf.logging.info("**** mlm generator scope **** %s", str(scope))

		# with tf.variable_scope("cls/predictions", reuse=tf.AUTO_REUSE):
		with tf.variable_scope(scope, reuse=tf.AUTO_REUSE):

			projection_width = self.config.emb_size

			with tf.variable_scope("transform"):
				input_tensor = tf.layers.dense(
						input_tensor,
						units=projection_width,
						activation=bert_modules.get_activation(self.config.hidden_act),
						kernel_initializer=bert_modules.create_initializer(
								self.config.initializer_range))

			output_bias = tf.get_variable(
					"output_bias",
					shape=[self.config.vocab_size],
					initializer=tf.zeros_initializer())
			# batch x seq x embedding
			logits = tf.einsum("abc,dc->abd", input_tensor, self.emb_mat)
			self.logits = tf.nn.bias_add(logits, output_bias)

	def get_pooled_output(self):
		return self.output

	def put_task_output(self, input_repres):
		self.task_repres = input_repres

	def get_task_output(self):
		return self.task_repres

	def get_sequence_output(self):
		return self.sequence_output

	def get_embedding_table(self):
		return self.emb_mat

	def get_embedding_projection_table(self):
		return None

	def get_sequence_output_logits(self):
		return self.logits

	

