import tensorflow as tf

from optimizer import distributed_optimizer as optimizer
from data_generator import distributed_tf_data_utils as tf_data_utils

# try:
# 	from .bert_model_fn import model_fn_builder
# 	from .bert_model_fn import rule_model_fn_builder
# except:
# 	from bert_model_fn import model_fn_builder
# 	from bert_model_fn import rule_model_fn_builder

# try:
# 	from .model_fn import model_fn_builder
# 	from .model_interface import model_config_parser
# 	from .model_data_interface import data_interface
# except:
# 	from model_fn import model_fn_builder
# 	from model_interface import model_config_parser
# 	from model_data_interface import data_interface

try:
	# from .model_fn import model_fn_builder
	from .model_interface import model_config_parser
	from .model_data_interface import data_interface
	from .model_fn_interface import model_fn_interface
	# from .model_distillation_fn import model_fn_builder as model_distillation_fn
except:
	# from model_fn import model_fn_builder
	from model_interface import model_config_parser
	from model_data_interface import data_interface
	# from model_distillation_fn import model_fn_builder as model_distillation_fn
	from model_fn_interface import model_fn_interface

import numpy as np
import tensorflow as tf
from bunch import Bunch
from model_io import model_io
import json

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

try:
	import tensorflow.contrib.pai_soar as pai
except Exception as e:
	pai = None

try:
	import horovod.tensorflow as hvd
except Exception as e:
	hvd = None

import time

def eval_fn(FLAGS,
				worker_count, 
				task_index, 
				is_chief, 
				target,
				init_checkpoint,
				train_file,
				dev_file,
				checkpoint_dir,
				is_debug,
				**kargs):

	graph = tf.Graph()
	with graph.as_default():
		import json
				
		# config = json.load(open(FLAGS.config_file, "r"))

		# config = Bunch(config)
		# config.use_one_hot_embeddings = True
		# config.scope = "bert"
		# config.dropout_prob = 0.1
		# config.label_type = "single_label"
		# config.model_type = FLAGS.model_type

		config = model_config_parser(FLAGS)

		# print(config, "==model config==")
		
		if FLAGS.if_shard == "0":
			train_size = FLAGS.train_size
			epoch = int(FLAGS.epoch / worker_count)
		elif FLAGS.if_shard == "1":
			train_size = int(FLAGS.train_size/worker_count)
			epoch = FLAGS.epoch
		else:
			train_size = int(FLAGS.train_size/worker_count)
			epoch = FLAGS.epoch

		init_lr = 2e-5

		label_dict = json.load(open(FLAGS.label_id))

		num_train_steps = int(
			train_size / FLAGS.batch_size * epoch)
		num_warmup_steps = int(num_train_steps * 0.1)

		num_storage_steps = int(train_size / FLAGS.batch_size)

		num_eval_steps = int(FLAGS.eval_size / FLAGS.batch_size)

		if is_debug == "0":
			num_storage_steps = 190
			num_eval_steps = 100
			num_train_steps = 200
		print("num_train_steps {}, num_eval_steps {}, num_storage_steps {}".format(num_train_steps, num_eval_steps, num_storage_steps))

		print(" model type {}".format(FLAGS.model_type))

		print(num_train_steps, num_warmup_steps, "=============")
		
		opt_config = Bunch({"init_lr":init_lr/worker_count, 
							"num_train_steps":num_train_steps,
							"num_warmup_steps":num_warmup_steps,
							"worker_count":worker_count,
							"opt_type":FLAGS.opt_type,
							"is_chief":is_chief,
							"train_op":kargs.get("train_op", "adam")})

		anneal_config = Bunch({
					"initial_value":1.0,
					"num_train_steps":num_train_steps
			})

		model_io_config = Bunch({"fix_lm":False})
		
		num_classes = FLAGS.num_classes

		if FLAGS.opt_type == "hvd" and hvd:
			checkpoint_dir = checkpoint_dir if task_index == 0 else None
		else:
			checkpoint_dir = checkpoint_dir
		print("==checkpoint_dir==", checkpoint_dir, is_chief)

		# if kargs.get("rule_model", "rule") == "rule":
		# 	model_fn_interface = rule_model_fn_builder
		# 	print("==apply rule model==")
		# else:
		# 	model_fn_interface = model_fn_builder
		# 	print("==apply normal model==")

		model_fn_builder = model_fn_interface(FLAGS)
		model_eval_fn = model_fn_builder(config, num_classes, init_checkpoint, 
												model_reuse=None, 
												load_pretrained=FLAGS.load_pretrained,
												opt_config=opt_config,
												model_io_config=model_io_config,
												exclude_scope="",
												not_storage_params=[],
												target=kargs.get("input_target", ""),
												output_type="sess",
												checkpoint_dir=checkpoint_dir,
												num_storage_steps=num_storage_steps,
												task_index=task_index,
												anneal_config=anneal_config,
												**kargs)

		print("==succeeded in building model==")
		
		def eval_metric_fn(features, eval_op_dict):
			logits = eval_op_dict["logits"]
			print(logits.get_shape(), "===logits shape===")
			pred_label = tf.argmax(logits, axis=-1, output_type=tf.int32)
			prob = tf.nn.softmax(logits)
			accuracy = correct = tf.equal(
				tf.cast(pred_label, tf.int32),
				tf.cast(features["label_ids"], tf.int32)
			)
			accuracy = tf.reduce_mean(tf.cast(correct, tf.float32))
			eval_op_dict['accuracy'] = accuracy
			eval_op_dict['prob'] = prob
			eval_op_dict['label_ids'] = features['label_ids']
			eval_op_dict['pred_label'] = pred_label

			return eval_op_dict

			# return {"accuracy":accuracy, "loss":eval_op_dict["loss"], 
			# 		"pred_label":pred_label, "label_ids":features["label_ids"],
			# 		"prob":prob,
			# 		"feature":eval_op_dict["feature"]}
		
		# name_to_features = {
		# 		"input_ids":
		# 				tf.FixedLenFeature([FLAGS.max_length], tf.int64),
		# 		"input_mask":
		# 				tf.FixedLenFeature([FLAGS.max_length], tf.int64),
		# 		"segment_ids":
		# 				tf.FixedLenFeature([FLAGS.max_length], tf.int64),
		# 		"label_ids":
		# 				tf.FixedLenFeature([], tf.int64),
		# }

		name_to_features = data_interface(FLAGS)

		def _decode_record(record, name_to_features):
			"""Decodes a record to a TensorFlow example.
			"""
			example = tf.parse_single_example(record, name_to_features)

			# tf.Example only supports tf.int64, but the TPU only supports tf.int32.
			# So cast all int64 to int32.
			for name in list(example.keys()):
				t = example[name]
				if t.dtype == tf.int64:
					t = tf.to_int32(t)
				example[name] = t

			return example

		def _decode_batch_record(record, name_to_features):
			example = tf.parse_example(record, name_to_features)
			# for name in list(example.keys()):
			# 	t = example[name]
			# 	if t.dtype == tf.int64:
			# 		t = tf.to_int32(t)
			# 	example[name] = t

			return example

		params = Bunch({})
		params.epoch = 0
		params.batch_size = FLAGS.batch_size

		print("==train_file==", train_file, params)

		if kargs.get("parse_type", "parse_single") == "parse_single":
			eval_features = tf_data_utils.eval_input_fn(dev_file,
										_decode_record, name_to_features, params, if_shard=FLAGS.if_shard,
										worker_count=worker_count,
										task_index=task_index)
		elif kargs.get("parse_type", "parse_single") == "parse_batch":
			eval_features = tf_data_utils.eval_batch_input_fn(dev_file,
										_decode_batch_record, name_to_features, params, if_shard=FLAGS.if_shard,
										worker_count=worker_count,
										task_index=task_index)

		print("==dev_file==", dev_file, kargs.get("rule_model", "rule"))

		eval_op_dict = model_eval_fn(eval_features, [], tf.estimator.ModeKeys.EVAL)
		eval_dict = eval_metric_fn(eval_features, eval_op_dict["eval"])

		print("==succeeded in building data and model==")

		sess_config = tf.ConfigProto(allow_soft_placement=False,
									log_device_placement=False)

		sess = tf.Session(config=sess_config)
		init_op = tf.group(tf.global_variables_initializer(), 
					tf.local_variables_initializer())

		sess.run(init_op)

		if FLAGS.load_pretrained != "yes":
			saver = tf.train.Saver(var_list=kargs.get("var_lst", None))
			saver.restore(sess, init_checkpoint)

		def eval_fn(eval_dict, sess):
			i = 0
			total_accuracy = 0
			eval_total_dict = {}
			while True:
				try:
					eval_result = sess.run(eval_dict)
					for key in eval_result:
						if key not in eval_total_dict:
							if key in ["pred_label", "label_ids", "prob", "feature"]:
								eval_total_dict[key] = []
								eval_total_dict[key].extend(eval_result[key].tolist())
							if key in ["accuracy", "loss"]:
								eval_total_dict[key] = 0.0
								eval_total_dict[key] += float(eval_result[key])
						else:
							if key in ["pred_label", "label_ids", "prob", "feature"]:
								eval_total_dict[key].extend(eval_result[key].tolist())
							if key in ["accuracy", "loss"]:
								eval_total_dict[key] += float(eval_result[key])

					i += 1
					# if len(set(eval_total_dict["pred_label"])) == len(list(label_dict["id2label"].keys())):
					# 	break
				except tf.errors.OutOfRangeError:
					print("End of dataset")
					break

			label_id = eval_total_dict["label_ids"]
			pred_label = eval_total_dict["pred_label"]

			label_dict_id = sorted(list(label_dict["id2label"].keys()))

			if len(label_dict_id) <= 10:
				result = classification_report(label_id, pred_label, 
					target_names=[label_dict["id2label"][key] for key in label_dict_id],
					digits=4)
				eval_total_dict["classification_report"] = result
				print("==classification report==")
				print(result, task_index)

			accuracy = accuracy_score(label_id, pred_label)
			print("==accuracy==", accuracy)
			return eval_total_dict

		hooks = []
		start_time = time.time()
		eval_finial_dict = eval_fn(eval_dict, sess)
		end_time = time.time()
		print("==forward time==", end_time - start_time)
		return eval_finial_dict
