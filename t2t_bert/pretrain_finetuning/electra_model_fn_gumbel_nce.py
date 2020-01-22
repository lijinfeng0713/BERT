import tensorflow as tf
import numpy as np
import re

try:
	from .discriminator_gumbel_nce import model_fn_builder as discriminator
	from .generator_gumbel import model_fn_builder as generator
	from .token_discriminator_nce import discriminator_metric_train, discriminator_metric_eval
	from .token_generator import generator_metric_fn_train, generator_metric_fn_eval
	from .token_discriminator_nce import nce_loss as nce_loss_fn
	from .generator_gumbel_normal import model_fn_builder as generator_normal
except:
	from discriminator_gumbel_nce import model_fn_builder as discriminator
	from generator_gumbel import model_fn_builder as generator
	from token_discriminator_nce import discriminator_metric_train, discriminator_metric_eval
	from token_generator import generator_metric_fn_train, generator_metric_fn_eval
	from token_discriminator_nce import nce_loss as nce_loss_fn
	from generator_gumbel_normal import model_fn_builder as generator_normal

import tensorflow as tf
import numpy as np
from optimizer import optimizer
from optimizer import distributed_optimizer

from model_io import model_io

import tensorflow as tf
from metric import tf_metrics

def get_train_op(generator_dict, discriminator_dict, optimizer_fn, opt_config,
				generator_config, discriminator_config,
				**kargs):
	if kargs.get('train_op_type', 'joint') == 'joint':
		tf.logging.info("***** original joint train op *****")
		tvars = []
		tvars.extend(discriminator_dict['tvars'])
		loss = kargs.get('dis_loss', 50.0) * discriminator_dict['loss']
		if kargs.get('joint_train', '1') == '1':
			tf.logging.info("****** joint generator and discriminator training *******")
			tvars.extend(generator_dict['tvars'])
			loss += generator_dict['loss']
		tvars = list(set(tvars))
		update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
		with tf.control_dependencies(update_ops):
			train_op = optimizer_fn.get_train_op(loss, list(set(tvars)),
							opt_config.init_lr, 
							opt_config.num_train_steps,
							**kargs)
	elif kargs.get('train_op_type', 'joint') in ['alternate', 'group']:
		generator_loss = generator_dict['loss'] - kargs.get('dis_loss', 1.0) * discriminator_dict['loss']
		discriminator_loss = kargs.get('dis_loss', 1.0) * discriminator_dict['loss']
		loss_dict = dict(zip(['generator', 'discriminator'], [generator_loss, discriminator_loss]))
		tvars_dict = dict(zip(['generator', 'discriminator'], [generator_dict['tvars'], discriminator_dict['tvars']]))
		init_lr_dict = dict(zip(['generator', 'discriminator'], [generator_config['init_lr'], discriminator_config['init_lr']]))
		optimizer_type_dict = dict(zip(['generator', 'discriminator'], [generator_config['optimizer_type'], discriminator_config['optimizer_type']]))
		
		if kargs.get('train_op_type', 'joint') == 'alternate':
			tf.logging.info("***** alternate train op for minmax *****")
			train_op_fn = optimizer_fn.get_alternate_train_op
		elif kargs.get('train_op_type', 'joint') == 'group':
			tf.logging.info("***** joint train op for minmax *****")
			train_op_fn = optimizer_fn.get_group_train_op

		update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
		with tf.control_dependencies(update_ops):
			train_op = train_op_fn(loss_dict, 
									tvars_dict, 
									init_lr_dict,
									optimizer_type_dict,
									opt_config.num_train_steps,
									**kargs)
	return train_op

def classifier_model_fn_builder(
						model_config_dict,
						num_labels_dict,
						init_checkpoint_dict,
						load_pretrained_dict,
						model_io_config={},
						opt_config={},
						exclude_scope_dict={},
						not_storage_params_dict={},
						target_dict={},
						**kargs):
	
	def model_fn(features, labels, mode, params):

		train_op_type = kargs.get('train_op_type', 'joint')
		if kargs.get('optimization_type', 'grl') == 'grl':
			generator_fn = generator(model_config_dict['generator'],
						num_labels_dict['generator'],
						init_checkpoint_dict['generator'],
						model_reuse=None,
						load_pretrained=load_pretrained_dict['generator'],
						model_io_config=model_io_config,
						opt_config=opt_config,
						exclude_scope=exclude_scope_dict.get('generator', ""),
						not_storage_params=not_storage_params_dict.get('generator', []),
						target=target_dict['generator'],
						**kargs)
			train_op_type = 'joint'
		elif kargs.get('optimization_type', 'grl') == 'minmax':
			generator_fn = generator_normal(model_config_dict['generator'],
						num_labels_dict['generator'],
						init_checkpoint_dict['generator'],
						model_reuse=None,
						load_pretrained=load_pretrained_dict['generator'],
						model_io_config=model_io_config,
						opt_config=opt_config,
						exclude_scope=exclude_scope_dict.get('generator', ""),
						not_storage_params=not_storage_params_dict.get('generator', []),
						target=target_dict['generator'],
						**kargs)
		else:
			generator_fn = generator(model_config_dict['generator'],
						num_labels_dict['generator'],
						init_checkpoint_dict['generator'],
						model_reuse=None,
						load_pretrained=load_pretrained_dict['generator'],
						model_io_config=model_io_config,
						opt_config=opt_config,
						exclude_scope=exclude_scope_dict.get('generator', ""),
						not_storage_params=not_storage_params_dict.get('generator', []),
						target=target_dict['generator'],
						**kargs)
		tf.logging.info("****** train_op_type:%s *******", train_op_type)
		tf.logging.info("****** optimization_type:%s *******", kargs.get('optimization_type', 'grl'))
		generator_dict = generator_fn(features, labels, mode, params)

		discriminator_fn = discriminator(model_config_dict['discriminator'],
					num_labels_dict['discriminator'],
					init_checkpoint_dict['discriminator'],
					model_reuse=None,
					load_pretrained=load_pretrained_dict['discriminator'],
					model_io_config=model_io_config,
					opt_config=opt_config,
					exclude_scope=exclude_scope_dict.get('discriminator', ""),
					not_storage_params=not_storage_params_dict.get('discriminator', []),
					target=target_dict['discriminator'],
					**kargs)

		tf.logging.info("****** true sampled_ids of discriminator *******")
		true_distriminator_features = {}
		true_distriminator_features['input_ids'] = generator_dict['sampled_input_ids']
		true_distriminator_features['input_mask'] = generator_dict['sampled_input_mask']
		true_distriminator_features['segment_ids'] = generator_dict['sampled_segment_ids']
		true_distriminator_features['input_ori_ids'] = generator_dict['sampled_input_ids']
		true_distriminator_features['next_sentence_labels'] = features['next_sentence_labels']
		true_distriminator_features['ori_input_ids'] = generator_dict['sampled_input_ids']

		true_distriminator_dict = discriminator_fn(true_distriminator_features, labels, 
													mode, params)

		fake_discriminator_features = {}
		if kargs.get('minmax_mode', 'corrupted') == 'corrupted':
			tf.logging.info("****** gumbel 3-D sampled_ids *******")
		elif kargs.get('minmax_mode', 'corrupted') == 'masked':
			fake_discriminator_features['ori_sampled_ids'] = generator_dict['output_ids']
			tf.logging.info("****** conditioanl sampled_ids *******")
		fake_discriminator_features['input_ids'] = generator_dict['sampled_ids']
		fake_discriminator_features['input_mask'] = generator_dict['sampled_input_mask']
		fake_discriminator_features['segment_ids'] = generator_dict['sampled_segment_ids']
		fake_discriminator_features['input_ori_ids'] = generator_dict['sampled_input_ids']
		fake_discriminator_features['next_sentence_labels'] = features['next_sentence_labels']
		fake_discriminator_features['ori_input_ids'] = generator_dict['sampled_ids']
		
		fake_discriminator_dict = discriminator_fn(fake_discriminator_features, labels, mode, params)

		nce_loss = nce_loss_fn(true_distriminator_dict, 	
													true_distriminator_features,
													fake_discriminator_dict, 
													fake_discriminator_features)

		model_io_fn = model_io.ModelIO(model_io_config)

		tvars = []

		loss = kargs.get('dis_loss', 1.0) *  nce_loss

		tvars.extend(fake_discriminator_dict['tvars'])

		if kargs.get('joint_train', '1') == '1':
			tf.logging.info("****** joint generator and discriminator training *******")
			tvars.extend(generator_dict['tvars'])
			loss += generator_dict['loss']
		tvars = list(set(tvars))

		var_checkpoint_dict_list = []
		for key in init_checkpoint_dict:
			if load_pretrained_dict[key] == "yes":
				if key == 'generator':
					tmp = {
							"tvars":generator_dict['tvars'],
							"init_checkpoint":init_checkpoint_dict['generator'],
							"exclude_scope":exclude_scope_dict[key],
							"restore_var_name":model_config_dict['generator'].get('restore_var_name', [])
					}
					if kargs.get("sharing_mode", "none") != "none":
						tmp['exclude_scope'] = ''
					var_checkpoint_dict_list.append(tmp)
				elif key == 'discriminator':
					tmp = {
						"tvars":discriminator_dict['tvars'],
						"init_checkpoint":init_checkpoint_dict['discriminator'],
						"exclude_scope":exclude_scope_dict[key],
						"restore_var_name":model_config_dict['discriminator'].get('restore_var_name', [])
					}
					var_checkpoint_dict_list.append(tmp)

		use_tpu = 1 if kargs.get('use_tpu', False) else 0
			
		if len(var_checkpoint_dict_list) >= 1:
			scaffold_fn = model_io_fn.load_multi_pretrained(var_checkpoint_dict_list,
											use_tpu=use_tpu)
		else:
			scaffold_fn = None

		if mode == tf.estimator.ModeKeys.TRAIN:

			if kargs.get('summary_debug', False):
				metric_dict = discriminator_metric_train(fake_discriminator_dict['per_example_loss'],
								fake_discriminator_dict['logits'], 
							generator_dict['sampled_input_ids'], 
							generator_dict['sampled_ids'],
							generator_dict['sampled_input_mask'])

				for key in metric_dict:
					tf.summary.scalar(key, metric_dict[key])
	
			if kargs.get('use_tpu', False):
				optimizer_fn = optimizer.Optimizer(opt_config)
				use_tpu = 1
			else:
				optimizer_fn = distributed_optimizer.Optimizer(opt_config)
				use_tpu = 0

			model_io_fn.print_params(tvars, string=", trainable params")
			
			update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
			with tf.control_dependencies(update_ops):
				train_op = optimizer_fn.get_train_op(loss, list(set(tvars)),
								opt_config.init_lr, 
								opt_config.num_train_steps,
								use_tpu=use_tpu)

			if kargs.get('use_tpu', False):
				estimator_spec = tf.contrib.tpu.TPUEstimatorSpec(
								mode=mode,
								loss=loss,
								train_op=train_op,
								scaffold_fn=scaffold_fn)
			else:
				estimator_spec = tf.estimator.EstimatorSpec(
								mode=mode, 
								loss=loss, 
								train_op=train_op)

			return estimator_spec

		elif mode == tf.estimator.ModeKeys.EVAL:

			if kargs.get('joint_train', '0') == '1':

				def joint_metric(masked_lm_example_loss, masked_lm_log_probs,
								masked_lm_ids, masked_lm_weights,
								next_sentence_example_loss, next_sentence_log_probs,
								next_sentence_labels,
								per_example_loss, logits,
								input_ori_ids, input_ids,
								input_mask):
					generator_metric = generator_metric_fn_eval(
										masked_lm_example_loss,
										masked_lm_log_probs,
										masked_lm_ids,
										masked_lm_weights,
										next_sentence_example_loss,
										next_sentence_log_probs,
										next_sentence_labels
										)
					discriminator_metric = discriminator_metric_eval(
							per_example_loss,
							logits, 
							input_ori_ids, 
							input_ids,
							input_mask)
					generator_metric.update(discriminator_metric)
					return generator_metric

				tpu_eval_metrics = (joint_metric, [
										generator_dict['masked_lm_example_loss'],
										generator_dict['masked_lm_log_probs'],
										generator_dict['masked_lm_ids'],
										generator_dict['masked_lm_weights'],
										generator_dict.get('next_sentence_example_loss', None),
										generator_dict.get('next_sentence_log_probs', None),
										generator_dict.get('next_sentence_labels', None),
										fake_discriminator_dict['per_example_loss'],
										fake_discriminator_dict['logits'], 
										generator_dict['sampled_input_ids'], 
										generator_dict['sampled_ids'],
										generator_dict['sampled_input_mask']])
				gpu_eval_metrics = joint_metric(generator_dict['masked_lm_example_loss'],
										generator_dict['masked_lm_log_probs'],
										generator_dict['masked_lm_ids'],
										generator_dict['masked_lm_weights'],
										generator_dict.get('next_sentence_example_loss', None),
										generator_dict.get('next_sentence_log_probs', None),
										generator_dict.get('next_sentence_labels', None),
										fake_discriminator_dict['per_example_loss'],
										fake_discriminator_dict['logits'], 
										generator_dict['sampled_input_ids'], 
										generator_dict['sampled_ids'],
										generator_dict['sampled_input_mask'])
			else:
				gpu_eval_metrics = discriminator_metric_eval(
								fake_discriminator_dict['per_example_loss'],
								fake_discriminator_dict['logits'], 
								generator_dict['sampled_input_ids'], 
								generator_dict['sampled_ids'],
								generator_dict['sampled_input_mask'])
				tpu_eval_metrics = (discriminator_metric_eval, [
											fake_discriminator_dict['per_example_loss'],
											fake_discriminator_dict['logits'], 
											generator_dict['sampled_input_ids'], 
											generator_dict['sampled_ids'],
											generator_dict['sampled_input_mask']
							])		

			if kargs.get('use_tpu', False):
				estimator_spec = tf.contrib.tpu.TPUEstimatorSpec(
							  mode=mode,
							  loss=loss,
							  eval_metrics=tpu_eval_metrics,
							  scaffold_fn=scaffold_fn)
			else:
				estimator_spec = tf.estimator.EstimatorSpec(mode=mode, 
								loss=loss,
								eval_metric_ops=gpu_eval_metrics)

			return estimator_spec
		else:
			raise NotImplementedError()

	return model_fn


