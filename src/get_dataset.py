"""
Created by jzc1104 on Jan 21 2020

Takes a directory with JSON files created with the red_input_file script, and creates a dataset for classification

"""
import jsonpickle, csv,os
import numpy as np

from read_input_file import get_filenames_in_dir
from sentence_embeddings import load_embeddings_model

import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
from nltk.tokenize import word_tokenize


def get_utterance_features(utt_complete):
    '''
    Receives a list generated by collect_period_utterances(), and extracts deeper features for each utterance, and puts everything in a binary row
    '''
    utterance_string=utt_complete[0].utterance
    utterance_types= utt_complete[0].utterance_type
    utterance_timestamp=utt_complete[0].timestamp
    speaker_pseudonym=utt_complete[1]
    speaker_type=utt_complete[2]
    previous_speaker_type=utt_complete[3]
    next_speaker_type=utt_complete[4]
    particip_structure=utt_complete[5]
    first_utt_in_turn=utt_complete[6]
    last_utt_in_turn=utt_complete[7]
    original_csvname=utt_complete[8]
    
    speaker_types=["teacher","student","other"]
    previous_speaker_types=["teacher","student","other","no_previous_speaker"]
    next_speaker_types=["teacher","student","other","no_next_speaker"]
    participation_structures=['Whole class discussion', 'Lecture', 'Small group + Instructor',  'Individual Work', 'Pair Work', 'Other']
    utterance_types_general=['Turn-Taking Facilitation', 
             'Metacognitive Modeling Questions', 
             'Behavior Management Questions', 
             'Teacher Open-Ended S/Q', 
             'Teacher Close-Ended S/Q', 
             
             'Student Open-Ended S/Q', 
             'Student Close-Ended S/Q', 
             'Student Close-Ended Response', 
             'Student Open-Ended Response', 
             'Student Explanation + Evidence' ]
    
    
    question_words=["what","What","why","Why","how","How","Is","do","Do","does","Does","can","Can","could","Could","where","Where","when","When"]
    key_words=["?","Student","\"","explain","Explain","right","no","No","yes","Yes","yeah","Yeah","because","Because"]
    key_phrases=["Go ahead","go ahead","right?", "Right.","How many","How much"]
    
    
    utterance_features=[original_csvname,utterance_string,speaker_pseudonym,utterance_timestamp]
    
    #THESE ARE THE CLASSES WE ARE LOOKING FOR
    for utt_type in utterance_types_general:
        if utt_type in utterance_types: utterance_features.append(True)
        else: utterance_features.append(False)

    #FEATURES TO PREDICT THE CLASSES
    for sp_type in speaker_types:
        if sp_type == speaker_type:utterance_features.append(True)
        else: utterance_features.append(False)
         
    for sp_type in previous_speaker_types:
        if sp_type == previous_speaker_type:utterance_features.append(True)
        else: utterance_features.append(False)
        
    for sp_type in next_speaker_types:
        if sp_type == next_speaker_type:utterance_features.append(True)
        else: utterance_features.append(False)
        
    utterance_features.append(first_utt_in_turn)
    utterance_features.append(last_utt_in_turn)
    
    for part_structure in participation_structures:
        if part_structure== particip_structure:utterance_features.append(True)
        else: utterance_features.append(False)
        

        
    #FEATURES RELATED TO THE STRING
    if len(utterance_string.split())>1: single_word=False
    else: single_word=True
    utterance_features.append(single_word)

    if type(utterance_string)!=str:
        print (utterance_string)
        print (type(utterance_string))
    
        print ("encoding error")
        utterance_string=utterance_string.decode("utf-8",errors='ignore')
        
    utterance_tokenized=word_tokenize(utterance_string)
    for word in question_words:
        if word in utterance_tokenized:utterance_features.append(True)
        else: utterance_features.append(False)
    for word in key_words:
        if word in utterance_tokenized:utterance_features.append(True)
        else: utterance_features.append(False)
    
    for phrase in key_phrases:
        if phrase in utterance_string: utterance_features.append(True)
        else: utterance_features.append(False)
        
    return utterance_features

def collect_period_utterances(period_object):
    '''
    Receives a Period object and collects all of its utterances along with some features into a list
    '''
    utterances_period=[]
    
    first_speaker=True
    for s,segment in enumerate(period_object.segments):
        #print "\t",s,segment.participation_type
        for t,turn in enumerate(segment.speaking_turns):
            
            if t ==len(segment.speaking_turns)-1: #If it's the last speaking turn in the segment
                if s==len(period_object.segments)-1: next_speaker_type="no_next_speaker" #if it's the last segment
                else: next_speaker_type=period_object.segments[s+1].speaking_turns[0].speaker_type #if there is another segment
            else: 
                next_speaker_type=segment.speaking_turns[t+1].speaker_type #if there is another turn in this segment, find out the type of the next speaker
                
            
            if first_speaker:
                previous_speaker_type="no_previous_speaker"
                first_speaker=False
            #print "\t","\t",turn.speaker_pseudonym, turn.speaker_type,previous_speaker_type,next_speaker_type#, turn.initial_time, turn.end_time, turn.cumulative_duration, turn.duration, "seconds"    
            for u,utterance in enumerate(turn.utterances):
                
                first_utterance_in_Turn=False
                if u==0: first_utterance_in_Turn=True
                
                last_utterance_in_Turn=False
                if u == len(turn.utterances)-1:last_utterance_in_Turn=True
                
                #print "\t","\t","\t",utterance.utterance,first_utterance_in_Turn,last_utterance_in_Turn
                new_utt=[utterance,turn.speaker_pseudonym,turn.speaker_type, previous_speaker_type,next_speaker_type, segment.participation_type,first_utterance_in_Turn,last_utterance_in_Turn,period_object.original_csv]
                
                utterances_period.append(new_utt)
            previous_speaker_type=turn.speaker_type
    return utterances_period

def extract_features_period(period_object,embedding_model,embedding_dimensionality):
    '''
    Gets a Period object and extracts for each utterance its features and their sentence embeddings
    '''
    print(period_object.original_csv)
    utterances_period=collect_period_utterances(period_object)
    print("Utterances collected")
    utterances_period_embeddings=get_utterances_embeddings(utterances_period,embedding_model)
    print("Embeddings calculated")
     
    features_utterances=[]
    for utt_complete,utt_embedding in zip(utterances_period,utterances_period_embeddings):
        #print (period.original_csv,utt_complete[0].utterance)
        utt_features=get_utterance_features(utt_complete)
        for i in range(embedding_dimensionality):
            utt_features.append(utt_embedding[i])
            
        features_utterances.append(utt_features)
    print ("Features extracted")
    return features_utterances
            

        
def get_utterances_embeddings(utterances_list,embed_model):
    '''
    Receives the list generated by collect_period_utterances(period_object) and generates a list with the sentence embeddings
    '''
    only_utt_strings=[utt[0].utterance for utt in utterances_list]
    utts_embeddings=np.array(embed_model(only_utt_strings)) #note the np.array()
    return utts_embeddings
            
            
def save_dataframe_as_CSV(dataframe,csv_filepath):
    '''
    Having a dataframe that contains features, utterance types and sentence embeddings, create a CSV file with the format of the input files of UCSD
    '''
    csv_header= ['Speaker', 
         'Time_Stamp', 
         'Transcript', 
         
         'Turn-Taking Facilitation', 
         'Metacognitive Modeling Questions', 
         'Behavior Management Questions', 
         'Teacher Open-Ended S/Q', 
         'Teacher Close-Ended S/Q', 
         'Student Open-Ended S/Q', 
         'Student Close-Ended S/Q', 
         'Student Close-Ended Response', 
         'Student Open-Ended Response', 
         'Student Explanation + Evidence', 
        
         'Whole class discussion', 
         'Lecture', 
         'Small group + Instructor', 
         'Individual Work', 
         'Pair Work', 
         'Other']    
    df_utt_types=["Utt_Turn_Taking","Metacognitive_Modelling","Utt_Behavior","Utt_Teacher_OpenQ","Utt_Teacher_CloseQ","Utt_Student_OpenQ","Utt_Student_CloseQ","Utt_Student_CloseR","Utt_Student_OpenR","Utt_Student_ExpEvi"]
    df_part_types=["Part_Discussion","Part_Lecture","Part_Small_Group","Part_Individual","Part_Pairs","Part_Other"]

    with open(csv_filepath,"w+",encoding = 'utf-8')  as output_csvfile:
        writer=csv.writer(output_csvfile,delimiter=",")
        writer.writerow(csv_header)
        
        speaker_index=dataframe.columns.get_loc("Speaker")
        speakers=dataframe.iloc[:,speaker_index].values
        
        timestamp_index=dataframe.columns.get_loc("Time_Stamp")
        timestamps=dataframe.iloc[:,timestamp_index].values
        
        utterance_index=dataframe.columns.get_loc("Utterance_String")
        utterances=dataframe.iloc[:,utterance_index].values
        
        predictions=[]
        for utt_type in df_utt_types:
            u_type_index=dataframe.columns.get_loc(utt_type)
            values=dataframe.iloc[:,u_type_index].values
            values=["1" if x else " " for x in values]
            predictions.append(values)
        
        participation_types=[]
        for part_type in df_part_types:
            p_type_index=dataframe.columns.get_loc(part_type)
            values=dataframe.iloc[:,p_type_index].values
            values=["1" if x else " " for x in values]
            participation_types.append(values)
        
        for i, speaker in enumerate(speakers):
            if timestamps[i]=="":speaker=""
            row=[speaker,timestamps[i],utterances[i]]
            for u_type in predictions:
                row.append(u_type[i])
            for p_type in participation_types:
                row.append(p_type[i])
            
            writer.writerow(row)
    print("File created:"+csv_filepath)

if __name__ == "__main__":
    
    import config as cfg
    json_folder=cfg.json_folder
    datasets_folder=cfg.datasets_folder
    os.environ['TFHUB_CACHE_DIR']=cfg.tf_cache_folder
    
    json_files=get_filenames_in_dir(json_folder,".json")
    all_periods=[]
    for filename in json_files:
        json_file=open(json_folder+"/"+filename)
        json_str = json_file.read()
        period_object = jsonpickle.decode(json_str)
        all_periods.append(period_object)
    
    embedding_types=["20","50","128","250","512","512t"]
    for embedding_type in embedding_types:    
        
        embedding_model=load_embeddings_model(embedding_type)
        print("Embedding model loaded: "+embedding_type)
        #Sometimes the cached models throw errors, particularly if the download process fails, then the 
        #corresponding files should be located and deleted, and then run the script again to try to download again the model
        if embedding_type=="512t":embedding_dimensionality=512
        else: embedding_dimensionality=int(embedding_type)
        
        headers=["Original_CSV_File","Utterance_String","Speaker","Time_Stamp",
                 "Utt_Turn_Taking","Metacognitive_Modelling","Utt_Behavior","Utt_Teacher_OpenQ","Utt_Teacher_CloseQ","Utt_Student_OpenQ","Utt_Student_CloseQ","Utt_Student_CloseR","Utt_Student_OpenR","Utt_Student_ExpEvi",
                 "Speaker_teacher","Speaker_student","Speaker_other","Previous_speaker_teacher","Previous_speaker_student","Previous_speaker_other","Previous_speaker_none",
                 "Next_speaker_teacher","Next_speaker_student","Next_speaker_other","Next_speaker_none",
                 "first_utterance_in_turn","last_utterance_in_turn",
                 "Part_Discussion","Part_Lecture","Part_Small_Group","Part_Individual","Part_Pairs","Part_Other",
                 "Single_Word",
                 "what","What","why","Why","how","How","Is","do","Do","does","Does","can","Can","could","Could","where","Where","when","When",
                 "QuestionMark","Student","Quotation","explain","Explain","right","no","No","yes","Yes","yeah","Yeah","because","Because",
                 "Go_ahead","go_ahead","right_questionmark", "Right_period","How_many","How_much"
                 ]
        for i in range(embedding_dimensionality):
            headers.append("Embedding_"+str(i))
        
        output_csv_filename="dataset_all_"+embedding_type+"dim.csv"
        outputfile_path=datasets_folder+"/"+output_csv_filename
       
        #PROCESS EACH PERIOD AND ADD TO FILE
        with open(outputfile_path,"w+",encoding="utf-8") as output_csv_file:
            dataset_writer = csv.writer(output_csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            dataset_writer.writerow(headers)
            all_utterances=[]
            
            for period in all_periods:    
                print()
                period_utterances_features=extract_features_period(period,embedding_model,embedding_dimensionality)
            
                for utt_features in period_utterances_features:
                    try:dataset_writer.writerow(utt_features)
                    except UnicodeEncodeError as e:
                        print (e)
                        utt_features[1]=utt_features[1].encode('utf-8')
                        print (utt_features[1])
                        dataset_writer.writerow(utt_features)
                print ("Features extracted and added to file")
                
            print ("\n All files processed and dataset file created: "+outputfile_path)