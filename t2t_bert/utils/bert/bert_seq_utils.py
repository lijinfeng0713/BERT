import tensorflow as tf
import numpy as np
from utils.bert import bert_utils

def get_finised_pos(token_seq, finished_index, max_length): 
	tmp_indices = tf.where(tf.equal(token_seq, int(finished_index)))
	finished_pos = tf.segment_min(tmp_indices[:, 1], tmp_indices[:, 0])
	sequence_mask = tf.sequence_mask(finished_pos+1, maxlen=max_length)
	return tf.cast(sequence_mask, tf.int32)

def get_finised_pos_v1(token_seq, finished_index, max_length): 
	seq_shape = bert_utils.get_shape_list(token_seq, expected_rank=[2,3])
	match_indices = tf.where(                          # [[5, 5, 2, 5, 4],
	tf.equal(finished_index, token_seq),                              #  [0, 5, 2, 3, 5],
		x=tf.range(seq_shape[1]) * tf.ones_like(token_seq),  #  [5, 1, 5, 5, 5]]
		y=(seq_shape[1])*tf.ones_like(token_seq))

	finished_pos = tf.reduce_min(match_indices, axis=1)
	sequence_mask = tf.sequence_mask(finished_pos+1, maxlen=max_length)
	return sequence_mask

def top_k_logits(logits, k):
	if k == 0:
		# no truncation
		return logits

	def _top_k():
		values, _ = tf.nn.top_k(logits, k=k)
		min_values = values[:, -1, tf.newaxis]
		return tf.where(
			logits < min_values,
			tf.ones_like(logits, dtype=logits.dtype) * -1e10,
			logits,
		)
	return tf.cond(
	   tf.equal(k, 0),
	   lambda: logits,
	   lambda: _top_k(),
	)

def sample_gumbel(shape, samples=1, eps=1e-20): 
	"""Sample from Gumbel(0, 1)"""
	if samples > 1:
		sample_shape = shape + [samples]
	else:
		sample_shape = shape
	U = tf.random_uniform(shape, minval=0.00001, maxval=0.99998)
	# return -tf.log(-tf.log(U + eps) + eps)
	return -tf.log(-tf.log(U))

def gumbel_softmax(logits, temperature, gumbel_samples=None, samples=1): 
	""" Draw a sample from the Gumbel-Softmax distribution"""
	input_shape_list = bert_utils.get_shape_list(logits, expected_rank=2)
	if samples > 1:
		logits = tf.expand_dims(logits, -1)
	if gumbel_samples is None:
		gumbel_samples = sample_gumbel(input_shape_list, samples)

	y = logits + gumbel_samples
	# here we consider inverse-temp-annealing
	tf.logging.info("==apply sampling based sampling and discrete relax==")
	return [tf.exp(tf.nn.log_softmax(y * temperature, axis=1)), 
			y]

# def sample_sequence_v1(model_api,
# 				model_config, 
# 				mode, 
# 				features,
# 				target="", 
# 				start_token=101, 
# 				context=None, 
# 				temperature=1, 
# 				n_samples=1,
# 				top_k=0,
# 				end_token=102,
# 				greedy_or_sample="sample",
# 				gumbel_prob=False,
# 				gumbel_temp=0.01,
# 				**kargs):

# 	# comment:sample for each time step is full-mask
# 	# seq_type="none", mask_type="left2right",

# 	input_shape = bert_utils.get_shape_list(features["input_ids"], expected_rank=[2,3])
# 	batch_size = input_shape[0]
# 	seq_length = input_shape[1]
# 	if start_token is None:
# 		assert context is not None, 'Specify exactly one of start_token and context!'
# 	else:
# 		assert context is None, 'Specify exactly one of start_token and context!'
# 		context = tf.fill([batch_size, 1], start_token)

# 	# Scalar dimensions referenced here:
# 	#   B = batch size (number of sequences)
# 	#   F = `from_tensor` sequence length
# 	#   T = `to_tensor` sequence length
# 	#   N = `num_attention_heads`
# 	#   H = `size_per_head`

# 	attention_head_size = int(model_config.hidden_size / model_config.num_attention_heads)

# 	# single layer present: [B, 2, N, T, H]
# 	# all layer present: [B, N_layer, 2, N, T, H]
# 	presents = tf.zeros((batch_size,
# 						model_config.num_hidden_layers, 
# 						 2, 
# 						 model_config.num_attention_heads, 
# 						 actual_length,
# 						 attention_head_size
# 						 ))

# 	samples = tf.cast(tf.zeros((batch_size, actual_length)), tf.int32)
# 	end_mask = tf.expand_dims(tf.one_hot(seq_length, actual_length), axis=(0))
# 	samples += end_token*tf.cast(end_mask, tf.int32) # make sure last token is end token
	
# 	start_mask = tf.expand_dims(tf.one_hot(0, actual_length), axis=(0))
# 	samples += start_token*tf.cast(start_mask, tf.int32) # make sure last token is end token

# 	if gumbel_prob:
# 		gumbel_probs = tf.zeros((batch_size,
# 						 seq_length,
# 						 model_config.vocab_size
# 						 ))
		
# 		start_probs = tf.cast(start_token * tf.ones((batch_size, 1)), tf.int32)
# 		start_one_hot = tf.one_hot(start_probs, model_config.vocab_size)
# 		gumbel_probs = tf.concat([tf.cast(start_one_hot, tf.float32), gumbel_probs], axis=1)
		

# 	def step(step, tokens, past=None):
# 		features = {}
# 		features['input_ids'] = tokens
# 		features['segment_ids'] = tf.zeros_like(tokens)
# 		if past is None:
# 			features['input_mask'] = tf.ones_like(tokens)
# 			features['past'] = None
# 		else:
# 			past_shape = bert_utils.get_shape_list(past, expected_rank=[6])
# 			features['input_mask'] = tf.cast(tf.ones((past_shape[0], step+1)), tf.int32)
# 			features['past'] = past[:, :, :, :, :step, :]

# 		inference_model = model_api(model_config, features, [],
# 							mode, target, reuse=tf.AUTO_REUSE,
# 							**kargs)

# 		logits = inference_model.get_sequence_output_logits()
# 		next_presents = inference_model.get_present()
		
# 		next_presents_shape = bert_utils.get_shape_list(next_presents, expected_rank=[6])
# 		print(presents.get_shape())
# 		if next_presents_shape[-2] > 0:
# 			print(next_presents_shape)
# 			print(next_presents.get_shape(), "===next presents shape===")
# #             mask = tf.expand_dims(tf.one_hot(step, actual_length), axis=(0, 1, 2, 3, 5))
# 			mask = tf.expand_dims(tf.one_hot(step, actual_length), axis=0)
# 			mask = tf.expand_dims(mask, axis=1)
# 			mask = tf.expand_dims(mask, axis=2)
# 			mask = tf.expand_dims(mask, axis=3)
# 			mask = tf.expand_dims(mask, axis=5)
# 			print(mask.get_shape(), "===mask shape===")
# 			past = past + tf.cast(mask, tf.float32) * next_presents
	   
# 		return {
# 			'logits': logits,
# 			'presents': past,
# 		}

# 	with tf.name_scope('sample_sequence'):
# 		# Don't feed the last context token -- leave that to the loop below
# 		# TODO: Would be slightly faster if we called step on the entire context,
# 		# rather than leaving the last token transformer calculation to the while loop.
		
# 		print(context[:, :-1].get_shape())
# 		context_output = step(0, context[:, :-1], past=presents)
		

# 		def get_samples_logits(samples, logits):
# 			batch_idxs = tf.range(0, tf.shape(samples)[0])
# 			batch_idxs = tf.expand_dims(batch_idxs, 1)

# 			idxs = tf.concat([batch_idxs, samples], 1)
# 			samples_logits = tf.expand_dims(tf.gather_nd(logits, idxs), -1)
# 			return samples_logits

# 		def body(i, past, prev, samples):
# 			print(prev.get_shape(), "==prev shape==")
# 			next_outputs = step(i, prev[:, tf.newaxis], past=past)
# 			logits = next_outputs['logits'][:, -1, :]  / tf.to_float(temperature)
# 			logits = tf.nn.log_softmax(logits, axis=-1)
# 			if greedy_or_sample == "sample":
# 				next_samples = tf.multinomial(logits, num_samples=1, output_dtype=tf.int32)
# 				next_samples = tf.squeeze(next_samples, axis=-1)
# 			elif greedy_or_sample == "greedy":
# 				next_samples = tf.argmax(logits, axis=-1)
# 			else:
# 				next_samples = tf.argmax(logits, axis=-1)
# 			print(next_samples.get_shape(), "==sample shape==")

# 			print(tf.one_hot(i, actual_length).get_shape(), "====shhhhape===")
# 			sample_mask = tf.expand_dims(tf.one_hot(i, actual_length), axis=(0)) # [1, seq, 1]
# 			print(sample_mask.get_shape(), "==sample mask shape==")
# 			print(samples.get_shape(), "==samples shape==")
# 			samples += tf.cast(sample_mask, tf.int32) * tf.cast(tf.expand_dims(next_samples, axis=-1), tf.int32)

# 			return [i+1, 
# 					next_outputs['presents'],
# 					next_samples, 
# 					samples]

# 		def gumbel_body(i, past, prev, samples, gumbel_probs):
# 			next_outputs = step(i, prev[:, tf.newaxis], past=past)
# 			logits = next_outputs['logits'][:, -1, :]  / tf.to_float(temperature)
# 			logits = tf.nn.log_softmax(logits, axis=-1)
# #             if greedy_or_sample == "sample":
# #                 next_samples = tf.multinomial(logits, num_samples=1, output_dtype=tf.int32)
# #                 next_samples = tf.squeeze(next_samples, axis=-1)
# #             elif greedy_or_sample == "greedy":
# #                 next_samples = tf.argmax(logits, axis=-1, keepdims=True)
# #             else:
# #                 next_samples = tf.argmax(logits, axis=-1, keepdims=True)
# 			next_gumbel_probs, _ = gumbel_softmax(logits, gumbel_temp, gumbel_samples=None, samples=1)
# 			next_samples = tf.cast(tf.argmax(next_gumbel_probs, axis=1), tf.int32)
# 			print(next_gumbel_probs.get_shape())
# 			gumbel_mask = tf.expand_dims(tf.expand_dims(tf.one_hot(i, actual_length), axis=0), axis=2) # [1, seq, 1]
# 			gumbel_probs += tf.cast(gumbel_mask, tf.float32) * tf.expand_dims(next_gumbel_probs, axis=1) # b x 1 x vocab
			
# 			sample_mask = tf.expand_dims(tf.one_hot(i, actual_length), axis=(0)) # [1, seq, 1]
# 			print(sample_mask.get_shape(), "==sample mask shape==")
# 			print(samples.get_shape(), "==samples shape==")
# 			samples += tf.cast(sample_mask, tf.int32) * tf.cast(tf.expand_dims(next_samples, axis=-1), tf.int32)

# 			return [i+1, 
# 					next_outputs['presents'],
# 					next_samples, 
# 					samples,
# 					gumbel_probs]

# 		if gumbel_prob:
# 			_, _, _, samples, gumbel_probs = tf.while_loop(
# 				cond=lambda i, _1, _2, _3, _4: i < seq_length,
# 				body=gumbel_body,
# 				loop_vars=[1,
# 					context_output['presents'],
# #                     presents,
# 					context[:, -1],
# 					samples,
# 					gumbel_probs
# 				],
# 				back_prop=False,
# 			)

# 		else:
# 			_, _, _, samples = tf.while_loop(
# 				cond=lambda i, _1, _2, _3: i < seq_length,
# 				body=body,
# 				loop_vars=[1,
# 					context_output['presents'],
# 					context[:, -1],
# 					samples
# 				],
# 				back_prop=False,
# 			)
# #         results = body(5, presents, context[:, -1], samples)
# #         samples = results[-1]
# #         print(samples)
# 		mask_sequence = get_finised_pos(samples, end_token, actual_length)
# 		print(mask_sequence.get_shape())
# 		samples *= tf.cast(mask_sequence, tf.int32)
# 		if gumbel_prob:
# 			gumbel_probs *= tf.expand_dims(tf.cast(mask_sequence, tf.float32), axis=-1)
# 			return samples[:, :actual_length], gumbel_probs[:, :seq_length, :]
# 		else:
# 			return samples[:, :actual_length], mask_sequence

def sample_sequence(model_api,
				model_config, 
				mode, 
				features,
				target="", 
				start_token=101, 
				batch_size=None, 
				seq_length=None,
				context=None, 
				temperature=1, 
				n_samples=1,
				top_k=0,
				end_token=102,
				greedy_or_sample="sample",
				gumbel_temp=0.01,
				estimator="straight_through",
				back_prop=True,
				swap_memory=True,
				attention_fixed_size=None,
				**kargs):

	input_shape = bert_utils.get_shape_list(features["input_ids"], expected_rank=[2,3])
	batch_size = input_shape[0]
	seq_length = input_shape[1]

	print(seq_length, "=====seq length======")

	print("=mask type=", kargs.get("seq_type", "seq2seq"), kargs.get("mask_type", "seq2seq"), "========")

	if context is None:
		assert start_token is not None, 'Specify exactly one of start_token and context!'
		context = tf.fill([batch_size, 1], start_token)
		context = tf.cast(context, tf.int32)
		print(context.get_shape(), "===init context shape===")
	else:
		context = tf.cast(context, tf.int32)
		context_shape = bert_utils.get_shape_list(context, expected_rank=[2])
		batch_size = input_shape[0]

	# if start_token is None:
	# 	assert context is not None, 'Specify exactly one of start_token and context!'
	# 	context = tf.cast(context, tf.int32)
	# else:
	# 	assert context is None, 'Specify exactly one of start_token and context!'
	# 	context = tf.fill([batch_size, 1], start_token)
	# 	context = tf.cast(context, tf.int32)
	# 	print(context.get_shape(), "===init context shape===")
		
	context_shape = bert_utils.get_shape_list(context, expected_rank=[2])
	actual_length = seq_length

	# Scalar dimensions referenced here:
	#   B = batch size (number of sequences)
	#   F = `from_tensor` sequence length
	#   T = `to_tensor` sequence length
	#   N = `num_attention_heads`
	#   H = `size_per_head`

	if attention_fixed_size:
		attention_head_size = attention_fixed_size
	else:
		attention_head_size = int(model_config.hidden_size / model_config.num_attention_heads)

	# single layer present: [B, 2, N, T, H]
	# all layer present: [B, N_layer, 2, N, T, H]
	presents = tf.zeros((batch_size,
						model_config.num_hidden_layers, 
						 2, 
						 model_config.num_attention_heads, 
						 actual_length,
						 attention_head_size
						 ))
	
	
	samples = tf.cast(tf.zeros((batch_size, actual_length)), tf.int32)
	end_mask = tf.expand_dims(tf.one_hot(actual_length-1, actual_length), axis=(0))
	samples += end_token*tf.cast(end_mask, tf.int32) # make sure last token is end token
	
#     samples += start_token * tf.einsum("ab,bc->ac", 
#                                     tf.cast(tf.ones((batch_size, tf.shape(start_mask)[0])), tf.int32), 
#                                      tf.cast(start_mask, tf.int32))
	
	start_mask = tf.one_hot(tf.range(0, context_shape[1]), actual_length)
	samples += tf.cast(tf.einsum("ab,bc->ac", 
									tf.cast(context, tf.float32), 
									 tf.cast(start_mask, tf.float32)), tf.int32)
	
	logits = tf.cast(tf.zeros((batch_size, actual_length)), tf.float32)
	
#     start_mask = tf.expand_dims(tf.one_hot(0, seq_length+1), axis=(0))
#     samples += start_token*tf.cast(start_mask, tf.int32) # make sure last token is end token

	if estimator in ["straight_through", "soft"]:
		gumbel_probs = tf.zeros((batch_size,
						 actual_length-context_shape[1],
						 model_config.vocab_size
						 ))
		
		start_probs = context
		start_one_hot = tf.one_hot(start_probs, model_config.vocab_size)
		gumbel_probs = tf.concat([tf.cast(start_one_hot, tf.float32), gumbel_probs], axis=1)
		
	def step(step, tokens, segment_ids=None, past=None):
		
		token_shape = bert_utils.get_shape_list(tokens, expected_rank=[2,3])
		
		features = {}
		features['input_ids'] = tokens
		if segment_ids is None:
			features['segment_ids'] = tf.cast(tf.zeros((token_shape[0], token_shape[1])), tf.int32)
		else:
			features['segment_ids'] = tf.cast(segment_ids, tf.int32)
		if past is None:
			features['input_mask'] = tf.cast(tf.ones((token_shape[0], token_shape[1])), tf.int32)
			features['past'] = None
		else:
			past_shape = bert_utils.get_shape_list(past, expected_rank=[6])
			features['input_mask'] = tf.cast(tf.ones((past_shape[0], step+token_shape[1])), tf.int32)
			features['past'] = past[:, :, :, :, :(step), :]

		inference_model = model_api(model_config, features, [],
							mode, target, reuse=tf.AUTO_REUSE,
							**kargs)

		logits = inference_model.get_sequence_output_logits()
		next_presents = inference_model.get_present()
		
		next_presents_shape = bert_utils.get_shape_list(next_presents, expected_rank=[6])

		print(presents.get_shape())
		if next_presents_shape[-2] > 0:
			print(next_presents_shape)
			print(next_presents.get_shape(), "===next presents shape===")
#             mask = tf.expand_dims(tf.one_hot(step, seq_length+1), axis=(0, 1, 2, 3, 5))
			mask = tf.cast(tf.one_hot(tf.range(step, step+token_shape[1]), actual_length), tf.float32)
#             tf.expand_dims(tf.one_hot(tf.range(step, step+token_shape[1]), seq_length+1), axis=0)
#             mask = tf.expand_dims(mask, axis=1)
#             mask = tf.expand_dims(mask, axis=2)
#             mask = tf.expand_dims(mask, axis=3)
#             mask = tf.expand_dims(mask, axis=5)
			print(mask.get_shape(), "===mask shape===")
			
			past = tf.einsum("abcdef,eg->abcdgf", next_presents, mask) + past
			
# #             past = past + tf.cast(mask, tf.float32) * next_presents
	   
		return {
			'logits': logits,
			'presents': past,
		}

	with tf.name_scope('sample_sequence'):
		# Don't feed the last context token -- leave that to the loop below
		# TODO: Would be slightly faster if we called step on the entire context,
		# rather than leaving the last token transformer calculation to the while loop.
		
		print(context[:, :-1].get_shape())
		init_context_shape = bert_utils.get_shape_list(context[:, :-1], expected_rank=[2,3])


		# def no_op(presents):
		# 	return {
		# 		"presents":presents,
		# 		"logits":tf.cast(tf.zeros((batch_size, actual_length)), tf.float32)
		# 	}

		# def set_context(presents):
		# 	init_segment_ids = tf.cast(tf.zeros((init_context_shape[0], init_context_shape[1])), tf.int32)
		# 	context_output = step(0, context[:, :-1], segment_ids=init_segment_ids, past=presents)
		# 	return context_output

		# context_output = tf.cond(tf.less_equal(init_context_shape[-1], 0),
		# 		lambda : no_op(presents),
		# 		lambda : set_context(presents))

		init_segment_ids = tf.cast(tf.zeros((init_context_shape[0], init_context_shape[1])), tf.int32)
		context_output = step(0, context[:, :-1], segment_ids=init_segment_ids, past=presents)
		
		def get_samples_logits(samples, logits):
			batch_idxs = tf.range(0, tf.shape(samples)[0])
			batch_idxs = tf.expand_dims(tf.cast(batch_idxs, tf.int32), 1)
			samples = tf.expand_dims(tf.cast(samples, tf.int32), 1)

			idxs = tf.concat([batch_idxs, samples], 1)
			sample_logits = tf.gather_nd(logits, idxs)
			return sample_logits

		def body(i, past, prev, samples, segment_ids, logits):
			print(prev.get_shape(), "==prev shape==", past.dtype, samples.dtype, segment_ids.dtype, i.dtype, logits.dtype)
			next_outputs = step(i-1, prev[:, tf.newaxis], segment_ids=segment_ids, past=past)
			next_logits = next_outputs['logits'][:, -1, :]  / tf.to_float(temperature)
			next_logits = tf.nn.log_softmax(next_logits, axis=-1)
			if greedy_or_sample == "sample":
				next_samples = tf.multinomial(next_logits, num_samples=1, output_dtype=tf.int32)
				next_samples = tf.squeeze(next_samples, axis=-1)
			elif greedy_or_sample == "greedy":
				next_samples = tf.argmax(next_logits, axis=-1)
			else:
				next_samples = tf.argmax(next_logits, axis=-1)
			next_samples = tf.cast(next_samples, tf.int32)
			print(next_samples.get_shape(), "==sample shape==")

			print(tf.one_hot(i, actual_length).get_shape(), "====shhhhape===")
			sample_mask = tf.expand_dims(tf.one_hot(i, actual_length), axis=(0)) # [1, seq, 1]
			print(sample_mask.get_shape(), "==sample mask shape==")
			print(samples.get_shape(), "==samples shape==")
			samples += tf.cast(sample_mask, tf.int32) * tf.cast(tf.expand_dims(next_samples, axis=-1), tf.int32)
			
			next_sample_logits = get_samples_logits(next_samples, next_logits)
			print(next_sample_logits.get_shape(), "===next sampleslogis shape==")
			logits += tf.cast(sample_mask, tf.float32) * tf.expand_dims(next_sample_logits, axis=-1)

			return [i+1, 
					next_outputs['presents'],
					next_samples, 
					samples,
					segment_ids,
				   logits]

		def gumbel_st_body(i, past, prev, samples, gumbel_probs, segment_ids, logits):
#             next_outputs = step(i-1, prev[:, tf.newaxis], past=past)
#             gumbel_probs[:, i-1, :]
			next_outputs = step(i-1, tf.expand_dims(gumbel_probs[:, i-1, :], axis=1), 
								segment_ids=segment_ids,    
								past=past)
			
			next_logits = next_outputs['logits'][:, -1, :]  / tf.to_float(temperature)
			next_logits = tf.nn.log_softmax(next_logits, axis=-1)
#             if greedy_or_sample == "sample":
#                 next_samples = tf.multinomial(logits, num_samples=1, output_dtype=tf.int32)
#                 next_samples = tf.squeeze(next_samples, axis=-1)
#             elif greedy_or_sample == "greedy":
#                 next_samples = tf.argmax(logits, axis=-1, keepdims=True)
#             else:
#                 next_samples = tf.argmax(logits, axis=-1, keepdims=True)
			next_gumbel_probs, _ = gumbel_softmax(next_logits, gumbel_temp, gumbel_samples=None, samples=1)
			next_samples = tf.cast(tf.argmax(next_gumbel_probs, axis=1), tf.int32)
			next_samples_onehot = tf.one_hot(next_samples, 
												   model_config.vocab_size,
													axis=1) # sampled multiminal id
			straight_through_onehot = tf.stop_gradient(next_samples_onehot-next_gumbel_probs)+next_gumbel_probs
			
			print(next_gumbel_probs.get_shape(), "=====gumbel====", straight_through_onehot.get_shape())
			gumbel_mask = tf.expand_dims(tf.expand_dims(tf.one_hot(i, actual_length), axis=0), axis=2) # [1, seq, 1]
			gumbel_probs += tf.cast(gumbel_mask, tf.float32) * tf.expand_dims(straight_through_onehot, axis=1) # b x 1 x vocab
			
			sample_mask = tf.expand_dims(tf.one_hot(i, actual_length), axis=(0)) # [1, seq, 1]
			print(sample_mask.get_shape(), "==sample mask shape==")
			print(samples.get_shape(), "==samples shape==")
			samples += tf.cast(sample_mask, tf.int32) * tf.cast(tf.expand_dims(next_samples, axis=-1), tf.int32)
			
			next_sample_logits = get_samples_logits(next_samples, next_logits)
			logits += tf.cast(sample_mask, tf.float32) * tf.expand_dims(next_sample_logits, axis=-1)
			
			return [i+1, 
					next_outputs['presents'],
					next_samples, 
					samples,
					gumbel_probs,
					segment_ids,
				   logits]
		
		def gumbel_soft_body(i, past, prev, samples, gumbel_probs, segment_ids, logits):
			next_outputs = step(i-1, prev[:, tf.newaxis], segment_ids=segment_ids, past=past)
	# #             gumbel_probs[:, i-1, :]
	# 			next_outputs = step(i-1, tf.expand_dims(gumbel_probs[:, i-1, :], axis=1), 
	# 								segment_ids=segment_ids,    
	# 								past=past)

			next_logits = next_outputs['logits'][:, -1, :]  / tf.to_float(temperature)
			next_logits = tf.nn.log_softmax(next_logits, axis=-1)
	#           
			# gumbel sample
			next_gumbel_probs, _ = gumbel_softmax(next_logits, gumbel_temp, gumbel_samples=None, samples=1)
			next_samples = tf.cast(tf.argmax(next_gumbel_probs, axis=1), tf.int32)
			# next_samples_onehot = tf.one_hot(next_samples, 
			# 									   model_config.vocab_size,
			# 										axis=1) # sampled multiminal id

			# straight-through token_matrix
			# straight_through_onehot = tf.stop_gradient(next_samples_onehot-next_gumbel_probs)+next_gumbel_probs

			print(next_gumbel_probs.get_shape())
			gumbel_mask = tf.expand_dims(tf.expand_dims(tf.one_hot(i, actual_length), axis=0), axis=2) # [1, seq, 1]
			gumbel_probs += tf.cast(gumbel_mask, tf.float32) * tf.expand_dims(next_gumbel_probs, axis=1) # b x 1 x vocab

			sample_mask = tf.expand_dims(tf.one_hot(i, actual_length), axis=(0)) # [1, seq]
			print(sample_mask.get_shape(), "==sample mask shape==")
			print(samples.get_shape(), "==samples shape==")
			samples += tf.cast(sample_mask, tf.int32) * tf.cast(tf.expand_dims(next_samples, axis=-1), tf.int32)

			next_sample_logits = get_samples_logits(next_samples, next_logits)
			logits += tf.cast(sample_mask, tf.float32) * tf.expand_dims(next_sample_logits, axis=-1)

			return [i+1, 
					next_outputs['presents'],
					next_samples, 
					samples,
					gumbel_probs,
					segment_ids,
				   logits]
		
		init_i = tf.cast(bert_utils.get_shape_list(context[:, :-1], expected_rank=[2,3])[1]+1, tf.int32)
		print(init_i, "=====init========================")
		if kargs.get("mask_type", "left2right") == 'left2right':
			print("==apply zeros segment===")
			left_segment_ids = tf.expand_dims(tf.cast(tf.zeros_like(context[:, -1]), tf.int32), axis=-1)
		elif kargs.get("mask_type", "left2right") == 'seq2seq':
			print("==apply ones segment===")
			left_segment_ids = tf.expand_dims(tf.cast(tf.ones_like(context[:, -1]), tf.int32), axis=-1)

		if estimator == "straight_through":
			final, presents, _, samples, gumbel_probs, _, logits = tf.while_loop(
				cond=lambda i, _1, _2, _3, _4, _5, _6: i < seq_length-1,
				body=gumbel_st_body,
				loop_vars=[init_i,
					context_output['presents'],
#                     presents,
					context[:, -1],
					samples,
					gumbel_probs,
					left_segment_ids,
					logits
				],
				back_prop=back_prop,
				swap_memory=swap_memory
			)
			
		elif estimator == "soft":
			final, presents, _, samples, gumbel_probs, _, logits = tf.while_loop(
				cond=lambda i, _1, _2, _3, _4, _5, _6: i < seq_length-1,
				body=gumbel_soft_body,
				loop_vars=[init_i,
					context_output['presents'],
#                     presents,
					context[:, -1],
					samples,
					gumbel_probs,
					left_segment_ids,
					logits
				],
				back_prop=back_prop,
				swap_memory=swap_memory
			)

		else:
			final, presents, _, samples, _, logits = tf.while_loop(
				cond=lambda i, _1, _2, _3, _4, _5: i < seq_length-1,
				body=body,
				loop_vars=[init_i,
					context_output['presents'],
#                     presents,
					context[:, -1],
					samples,
					left_segment_ids,
					logits
				],
				back_prop=back_prop,
				swap_memory=swap_memory
			)

#         results = body(5, presents, context[:, -1], samples)
#         samples = results[-1]
#         print(samples)
		mask_sequence = get_finised_pos_v1(samples, end_token, actual_length)
		print(mask_sequence.get_shape(), "==mask shape==")
		samples *= tf.cast(mask_sequence, tf.int32)
		logits *= tf.cast(mask_sequence, tf.float32)
		if estimator in ["straight_through", "soft"]:
			gumbel_probs *= tf.expand_dims(tf.cast(mask_sequence, tf.float32), axis=-1)
			return {
				"samples":samples,
				"mask_sequence":mask_sequence,
				"gumbel_probs":gumbel_probs,
				"presents":presents,
				"logits":logits,
				"final":final
			}
			# return samples, mask_sequence, gumbel_probs, presents, logits, final
		else:
			return {
				"samples":samples,
				"mask_sequence":mask_sequence,
				"presents":presents,
				"logits":logits,
				"final":final
			}
			# return samples, mask_sequence, presents, logits, final