import json
import numpy as np
from datasets import Dataset
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          TrainingArguments, Trainer)

INTENTS = ["takeoff_clearance", "landing_clearance", "heading_change",
           "altitude_change", "frequency_change", "hold", "go_around",
           "unknown"]

MODEL_NAME = "distilbert-base-uncased"


def load_jsonl(path):
    rows = [json.loads(line) for line in open(path)]
    return Dataset.from_list(rows)


train_ds = load_jsonl("bert_train.jsonl")
test_ds = load_jsonl("bert_test.jsonl")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


def tokenize(batch):
    return tokenizer(batch["text"], truncation=True, max_length=64)


train_ds = train_ds.map(tokenize, batched=True)
test_ds = test_ds.map(tokenize, batched=True)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(INTENTS),
    id2label={i: n for i, n in enumerate(INTENTS)},
    label2id={n: i for i, n in enumerate(INTENTS)},
)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {"accuracy": (preds == labels).mean()}


args = TrainingArguments(
    output_dir="bert_checkpoints",
    num_train_epochs=5,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    eval_strategy="epoch",
    save_strategy="no",
    fp16=True,                      # your 4060 supports this — 2x speed
    logging_steps=20,
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    eval_dataset=test_ds,
    compute_metrics=compute_metrics,
    processing_class=tokenizer,
)

trainer.train()

# Final numbers + save
results = trainer.evaluate()
print(f"\nFinal test accuracy: {results['eval_accuracy']:.1%}")

model.save_pretrained("bert_intent_model")
tokenizer.save_pretrained("bert_intent_model")
print("Saved to bert_intent_model/")