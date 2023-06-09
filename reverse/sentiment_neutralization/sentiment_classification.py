"""Sentiment Classification Code."""

import os
import pickle
import re
import pandas as pd
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.layers import Input, Dense, Embedding, LSTM
from keras.models import Model
from keras.callbacks import ModelCheckpoint
from sklearn.model_selection import train_test_split
from keras_self_attention import SeqSelfAttention
import neutralisation_params

def classification_labels(row):
    """Function for mapping labels"""
    if row["label"] == 1:
        return "Negative"
    return "Positive"

def main():
    """Function for classifying sentences into positive and negative"""
    data_dir = neutralisation_params.DATA_DIR
    model_dir = neutralisation_params.RESULT_DIR

    # Data reading and pre-processing
    data = pd.read_csv(os.path.join(data_dir, 'sentiment_data.csv'), encoding="ISO-8859-1")
    data.columns = ["text", "label"]
    data['text'] = data['text'].apply(lambda x: x.lower())
    data["sentiment"] = data.apply(classification_labels, axis=1)

    data.drop("label", axis=1, inplace=True)
    data['text'] = data['text'].apply(lambda x: x.lower())
    data['text'] = data['text'].apply((lambda x: re.sub('[^a-zA-z0-9\s]', '', x)))

    maxlen = neutralisation_params.maxlen
    max_features = neutralisation_params.max_features
    tokenizer = Tokenizer(num_words=max_features, split=' ')
    tokenizer.fit_on_texts(data['text'].values)
    X = tokenizer.texts_to_sequences(data['text'].values)
    X = pad_sequences(X, maxlen=maxlen)
    # reverse_word_map = dict(map(reversed, tokenizer.word_index.items()))
    token_path = os.path.join(model_dir, neutralisation_params.token_file_path)
    complete_token_path = token_path + ".pickle"
    with open(complete_token_path, 'wb') as handle:
        pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(X.shape)

    #Model Building
    embed_dim = neutralisation_params.embed_dim
    inputs = Input(shape=(maxlen,))
    emb1 = Embedding(max_features, embed_dim, mask_zero=True)(inputs)
    lstm1 = LSTM(200, return_sequences=True)(emb1)
    lstm_out, att_weights = SeqSelfAttention(attention_activation='sigmoid', return_attention=True)(lstm1)
    lstm2 = LSTM(150, return_sequences=False, trainable=False)(lstm_out)
    # d1 = Dense(50, activation='sigmoid')(lstm2)
    # d2 = Dense(10, activation='sigmoid')(d1)
    outputs = Dense(2, activation='sigmoid')(lstm2)
    model = Model(inputs=[inputs], outputs=outputs)
    print(model.summary())

    Y = pd.get_dummies(data['sentiment']).values
    x_train, x_test, y_train, y_test = train_test_split(X, Y, test_size=0.1, random_state=42)
    print(x_train.shape, y_train.shape)
    print(x_test.shape, y_test.shape)
    batch_size = neutralisation_params.batch_size
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

    model_name = neutralisation_params.model_name
    filepath = os.path.join(model_dir, model_name) + "_intermediate.hdf5"
    checkpoint = ModelCheckpoint(filepath, monitor='val_acc', verbose=1,
                                 save_best_only=True, mode='max')
    callbacks_list = [checkpoint]

    epochs = neutralisation_params.epochs
    model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs,
              validation_data=(x_test, y_test), verbose=1, callbacks=callbacks_list)

    print("Training has finished. Model save at ", os.path.join(model_dir, model_name) + "_final.hdf5")
    model.save(os.path.join(model_dir, model_name) + "_final.hdf5")
    score, acc = model.evaluate(x_test, y_test, batch_size=batch_size)
    print('Test score:', score)
    print('Test accuracy:', acc)

    print('Test score:', score)
    print('Test accuracy:', acc)

if __name__ == '__main__':
	main()
