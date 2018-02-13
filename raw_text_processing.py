###########################################################################
# Pre-processing raw text

# Date: November 2017
###########################################################################
import os
import re
import nltk # Natural Language toolkit
from nltk.tokenize import sent_tokenize, word_tokenize # form tokens from words/sentences
import string
import csv
from datetime import datetime
from collections import namedtuple
from itertools import imap # set up namedtuple
########################################################################
## READING AND TOKENIZATION OF RAW TEXT (PRE-PROCESSING)

basic_pronouns = "I Me You She He Him It We Us They Them Myself Yourself Himself Herself Itself Themselves My your Her Its Our Their His"
possessive_pronouns = "mine yours his hers ours theirs"
reflexive_pronouns = "myself yourself himself herself itself oneself ourselves yourselves themselves"
relative_pronouns = "that whic who whose whom where when"


def readFile(filename):
	file_remove_extra = []
	with open(filename, "r") as given_file:
		string_words = given_file.read()
		string_words = string_words.replace("\n", " ")
		string_words = string_words.replace(";" , " ")
		string_words = string_words.replace("--", " ")
		string_words = string_words.replace("_", "")
		string_words = string_words.replace("Mr.", "Mr") # period created breaks when spliting
		string_words = string_words.replace("Ms.", "Ms")
		string_words = string_words.replace("Mrs.", "Mrs")
		string_words = string_words.replace("Dr.", "Dr")
		string_words = re.sub(r'[\x90-\xff]', '', string_words, flags=re.IGNORECASE) # remove unicode
		string_words = re.sub(r'[\x80-\xff]', '', string_words, flags=re.IGNORECASE) # remove unicode
		file_remove_extra = string_words.split(' ')
		file_remove_extra = filter(None, file_remove_extra) # remove empty strings from list
	return file_remove_extra

def tokenizeSentence(string_sentence):
	'''EXAMPLE
	{60: 'After rather a long silence, the commander resumed the conversation.'}
	'''
	tokens_sentence_dict = {} # returns dict with {token location in text #: sentence}
	tokens_sent = string_sentence.split('.')
	for i in range(len(tokens_sent)):
		if tokens_sent[i] != '':
			tokens_sentence_dict[i] = tokens_sent[i].strip() #adds to dictionary and strips away excess whitespace
	#print(tokens_sentence_dict)
	return tokens_sentence_dict

def partsOfSpeech(token_dict):
	'''EXAMPLE
	60: ('After rather a long silence, the commander resumed the conversation.', 
	[('After', 'IN'), ('rather', 'RB'), ('a', 'DT'), ('long', 'JJ'), ('silence', 'NN'),
	 (',', ','), ('the', 'DT'), ('commander', 'NN'), ('resumed', 'VBD'), ('the', 'DT'), 
	 ('conversation', 'NN'), ('.', '.')])}
	'''
	from subprocess import check_output
	import progressbar as pb
	widgets = ['Running POS tagger: ', pb.Percentage(), ' ', 
				pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]
	timer = pb.ProgressBar(widgets=widgets, maxval=len(token_dict)).start()

	for i in range(len(token_dict)):
		timer.update(i)
		no_punc = token_dict[i].translate(None, string.punctuation) # remove puncuation from part of speech tagging
		pos_tagged = check_output(["./3_run_text.sh", token_dict[i]])
		if "docker not running, required to run syntaxnet" not in pos_tagged:
			pos_tagged = process_POS_conll(pos_tagged) # process conll output from shell
			token_dict[i] = (token_dict[i], pos_tagged) # adds part of speech tag for each word in the sentence
		else:
			print("\n\tWARNING: docker not running, cannot run syntaxnet for POS, exiting")
			exit()
	timer.finish()
	return token_dict

def process_POS_conll(conll_output):
	'''
	['1', 'At', '_', 'ADP', 'IN', '_', '13', 'prep', '_', '_']
	['2', 'the', '_', 'DET', 'DT', '_', '3', 'det', '_', '_']
	['3', 'period', '_', 'NOUN', 'NN', '_', '1', 'pobj', '_', '_']
	['4', 'when', '_', 'ADV', 'WRB', '_', '7', 'advmod', '_', '_']
	['5', 'these', '_', 'DET', 'DT', '_', '6', 'det', '_', '_']
	['6', 'events', '_', 'NOUN', 'NNS', '_', '7', 'nsubj', '_', '_']
	['7', 'took', '_', 'VERB', 'VBD', '_', '3', 'rcmod', '_', '_']
	['8', 'place', '_', 'NOUN', 'NN', '_', '7', 'dobj', '_', '_']
	'''
	pos_processed = conll_output
	#print(pos_processed)
	start_data = 0
	pos_processed = re.sub("\t", ",", pos_processed.strip())
	pos_processed = re.sub(",", " ", pos_processed.strip())
	pos_processed = pos_processed.splitlines()
	for i in range(len(pos_processed)):
		pos_processed[i] = pos_processed[i].split(" ")
		#print(pos_processed[i])
	return pos_processed

def percentagePronounsNouns(total_words, csv_dict):
	# return the percentage of the text that is pronouns vs. nouns
	nouns_count = [pos.XPOSTAG for _, pos in csv_dict.iteritems()].count("NNP")
	print("\npercent nouns = {0:.3f}%".format((float(nouns_count)/float(total_words))*100))
	pronouns_count = [pos.XPOSTAG for _, pos in csv_dict.iteritems()].count("PRP")
	pronoun_percentage = float(pronouns_count)/float(total_words)
	print("percent pronouns = {0:.3f}%".format(pronoun_percentage*100.0))
	return pronoun_percentage

def findNamedEntityAndPronoun(pos_dict):
	# find proper nouns and full name (first/last name)
	named_dict = {}
	named_temp_lst = []
	pos_type_lst = []
	for row, pos_named in pos_dict.iteritems():
		if "NN" in pos_named.XPOSTAG or "POS" in pos_named.XPOSTAG:
			pos_type_lst.append((int(pos_named.SENTENCE_INDEX), int(pos_named.ID), pos_named.FORM, int(pos_named.SENTENCE_LENGTH), pos_named.XPOSTAG))
	print(pos_type_lst)
	total_sentence_indices = list(set([i[0] for i in pos_type_lst]))
	sub_sentences = []
	for index in total_sentence_indices:
		# create sub sentences for each sentence [[0], [1])
		sub_sentences.append([x for x in pos_type_lst if x[0] == index])

	'''
	for row, pos_named in pos_dict.iteritems():
		#print(pos_named.SENTENCE_INDEX)
		#print(pos_named.FORM)
		#print(pos_named.XPOSTAG)
		if "NN" in pos_named.XPOSTAG:
			named_lst[int(pos_named.SENTENCE_INDEX)], int(row), pos_named.XPOSTAG, pos_named.FORM])
		#if "PRP" in pos_named.XPOSTAG:
		#	named_lst.append([int(pos_named.SENTENCE_INDEX), int(row), pos_named.XPOSTAG, pos_named.FORM])
		if "POS" in pos_named.XPOSTAG:
			named_lst.append([int(pos_named.SENTENCE_INDEX), int(row), pos_named.XPOSTAG, pos_named.FORM])
	'''

########################################################################
## Output pos into csv
def outputCSVconll(filename, dict_parts_speech, filednames):
	# save conll parser and pos to csv
	'''
	0 - ID (index in sentence), index starts at 1
	1 - FORM (exact word)
	2 - LEMMA (stem of word form)
	3 - UPOSTAG (universal pos tag)
	4 - XPOSTAG (Language-specific part-of-speech tag)
	5 - FEATS (List of morphological features)
	6 - HEAD (Head of the current token, which is either a value of ID or zero (0))
	7 - DEPREL (Universal Stanford dependency relation to the HEAD (root iff HEAD = 0))
	8 - DEPS (List of secondary dependencies)
	9 - MISC (other annotation)
	'''
	given_file = os.path.basename(os.path.splitext(filename)[0]) # return only the filename and not the extension
	output_filename = "pos_{0}.csv".format(given_file.upper())

	with open('csv_pos/{0}'.format(output_filename), 'w+') as pos_data:
		writer = csv.DictWriter(pos_data, fieldnames=fieldnames)
		writer.writeheader() 
		for i in range(len(dict_parts_speech)):
			sentence_pos_lst = dict_parts_speech[i][1]
			for pos in sentence_pos_lst:
				writer.writerow({'SENTENCE_INDEX': i, 
								'FORM': pos[1],
								'XPOSTAG': pos[4],
								'UPOSTAG': pos[3],
								'ID': pos[0],
								'SENTENCE_LENGTH': len(dict_parts_speech[i][0].split()),
								'LEMMA': pos[2],
								'FEATS': pos[5],
								'HEAD': pos[6],
								'DEPREL': pos[7],
								'DEPS':pos[8],
								'MISC': pos[9],
								'SENTENCE': dict_parts_speech[i][0]
								})

	print("\nCSV POS output saved as {0}".format(output_filename))
########################################################################
## Parse Arguments, running main

if __name__ == '__main__':
	start_time = datetime.now()
	import argparse
	parser = argparse.ArgumentParser(description="flag format given as: -F <filename>")
	parser.add_argument('-F', '-filename', help="filename from Raw_Text directory")
	args = parser.parse_args()

	filename = args.F

	if filename is None:
		print("\n\tWARNING: File not given to tokenize, exiting...\n")
		exit()

	tokens_in_order = readFile(filename)
	tokens_as_string = " ".join(tokens_in_order)
	tokens_as_string = tokens_as_string.translate(None, "\r")

	token_sentence_dict = tokenizeSentence(tokens_as_string)
	#print(token_sentence_dict) # TODO: switch to namedTuples

	# check to see if file has already been saved in csv, otherwise run script
	given_file = os.path.basename(os.path.splitext(filename)[0]) # return only the filename and not the extension
	output_filename = "pos_{0}.csv".format(given_file.upper())
	csv_local_dir = "{0}/csv_pos/{1}".format(os.getcwd(), output_filename)

	fieldnames = ['SENTENCE_INDEX',
				'FORM',
				'XPOSTAG',
				'UPOSTAG',
				'ID',
				'SENTENCE_LENGTH',
				'LEMMA',
				'FEATS',
				'HEAD',
				'DEPREL',
				'DEPS',
				'MISC',
				'SENTENCE'
				]

	# if file has been modified more recently than the associated csv
	file_has_been_modified_recently = False
	if os.path.isfile(csv_local_dir): # if file exists, then check if modified
		file_has_been_modified_recently = os.path.getmtime("{0}/{1}".format(os.getcwd(), filename)) > os.path.getmtime(csv_local_dir)
	# if file does not exist in the csv folder
	if not os.path.isfile(csv_local_dir) or file_has_been_modified_recently: 
		#print("pos needs to be calculated...")
		dict_parts_speech = partsOfSpeech(token_sentence_dict)
		outputCSVconll(filename, dict_parts_speech, fieldnames)

	

	#TODO Next: import local file to predict male/female (he/she) with a given list of names
	#x number of sentences around to find proper noun
	#from sklearn.externals import joblib # save model to load
	#loaded_gender_model = joblib.load('name_preprocessing/gender_saved_model_0.853992787223.sav')
	#test_name = ["Nemo"]
	#print(loaded_gender_model.score(test_name))
	#run gender tag once on the entire text, tag male/female and use for predictions
	
	# create named tuple from csv row
	PosCSV = namedtuple('PosCSV', fieldnames)
	pos_dict = {}
	total_words = 0
	with open(csv_local_dir, "rb") as csv_file:
		csvreader = csv.reader(csv_file)
		next(csvreader) # skip header
		id_count = 0
		for line in csvreader:
			pos_named_tuple = PosCSV._make(line)
			pos_dict[id_count] = pos_named_tuple
			id_count += 1
			if pos_named_tuple.MISC != 'punct' and pos_named_tuple.XPOSTAG != 'POS': # if row isn't puntuation or 's
				total_words += 1
	print(total_words)
	named_ent_lst = findNamedEntityAndPronoun(pos_dict)
	pronoun_percentage = percentagePronounsNouns(total_words, pos_dict) # TODO: update nouns list with only named enitites

	# TODO: identify dialouge to create it as its own sentence


	print("\nPre-processing ran for {0}".format(datetime.now() - start_time))

'''
def mostCommonPronouns(raw_text):
	# returns a dictionary of the most common pronouns in the text with their occureance #
	#{'it': 1291, 'him': 213, 'yourself': 16, 'his': 519, 'our': 292, 'your': 122}

	pronoun_common = {}
	from collections import Counter

	raw_words = re.findall(r'\w+', raw_text)

	total_words = [word.lower() for word in raw_words]
	word_counts = Counter(total_words)
		
	tag_pronoun = ["PRP", "PRP$"]

	for word in word_counts:
		captilize_options = [word.capitalize(), word.lower()] # dealing with ME seen as NN instead of PRP
		for options in captilize_options:
			if nltk.pos_tag(nltk.word_tokenize(options))[0][1] in tag_pronoun: # if word is a pronoun, then store it
				if options.lower() in basic_pronouns.lower().split():
					pronoun_common[word.lower()] = word_counts[word]

	# testing that it found the right pronouns (not in basic_pronouns)
	#if len(pronoun_common.keys()) != len(basic_pronouns.lower().split()):
	#	for found in pronoun_common.keys():
	#		if found not in basic_pronouns.lower().split():
	#			print("\n\tWARNING: INCORRECT PRONOUNS FOUND ==> {0}\n".format(found))

	return pronoun_common


def indexPronoun(token_dict, pronoun_dict):
	# stores pronoun and location in sentence for each sentence
	#{0: (['I'], [8]), 1: (['my', 'me'], [3, 21]), 2: (['I'], [5])}

	index_pronoun_dict = {}
	pronouns_in_txt = pronoun_dict.keys()
	for index, sentence in token_dict.iteritems():
		pronoun_in_sentence = []
		pronoun_location = []

		for word_index in range(len(sentence.split())):
			if sentence.split()[word_index].lower() in pronouns_in_txt:
				pronoun_in_sentence.append(sentence.split()[word_index])
				pronoun_location.append(word_index)
		index_pronoun_dict[index] = (pronoun_in_sentence, pronoun_location)

	return index_pronoun_dict
'''
