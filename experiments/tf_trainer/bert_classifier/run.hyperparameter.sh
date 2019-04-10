#!/bin/bash

source "tf_trainer/common/dataset_config.sh"
DATETIME=$(date '+%Y%m%d_%H%M%S')
MODEL_NAME="bert_classifier"
MODEL_NAME_DATA="${MODEL_NAME}_$1"
JOB_DIR="${MODEL_PARENT_DIR}/${USER}/${MODEL_NAME_DATA}/${DATETIME}"

gcloud ml-engine jobs submit training tf_trainer_${MODEL_NAME_DATA}_${USER}_${DATETIME} \
    --job-dir=${JOB_DIR} \
    --runtime-version=1.10 \
    --module-name="tf_trainer.${MODEL_NAME}.run" \
    --package-path=tf_trainer \
    --region=us-east1 \
    --verbosity=debug \
    --config="tf_trainer/${MODEL_NAME}/hparam_config_$1.yaml" \
    -- \
    --train_path=$train_path \
    --validate_path=$valid_path \
    --model_dir="${JOB_DIR}/model_dir" \
    --is_embedding_trainable=False \
    --train_steps=$train_steps \
    --eval_period=$eval_period \
    --eval_steps=$eval_steps \
    --labels=$labels \
    --label_dtypes=$label_dtypes \
    --preprocess_in_tf=False \
    --model_spec="https://tfhub.dev/google/bert_uncased_L-12_H-768_A-12/1"


echo "Model dir:"
echo ${JOB_DIR}/model_dir
