import requests
import json
import gradio as gr
from datetime import datetime
import time
import random
import boto3
import os 

#Fill in your correct configuration

invoke_url = '' # 更新你的apigw url

chinese_index = 'smart_search_qa_test'
english_index = ''

cn_embedding_endpoint = 'huggingface-inference-eb'
cn_llm_endpoint = 'pytorch-inference-llm-v1'
en_embedding_endpoint = ''
en_llm_endpoint = ''


#Modify the default prompt as needed
chinese_prompt = """基于以下已知信息，简洁和专业的来回答用户的问题，并告知是依据哪些信息来进行回答的。
   如果无法从中得到答案，请说 "根据已知信息无法回答该问题" 或 "没有提供足够的相关信息"，不允许在答案中添加编造成分，答案请使用中文。
    
            问题: {question}
            =========
            {context}
            =========
            答案:"""

english_prompt = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.
{context}

Question: {question}
Answer:"""                                


chinses_summarize_prompt="""请根据访客与客服的通话记录，写一段访客提出问题的摘要，突出显示与亚马逊云服务相关的要点, 摘要不需要有客服的相关内容:
{text}

摘要是:"""

english_summarize_prompt="""Based on the call records between the visitor and the customer service, write a summary of the visitor's questions, highlighting the key points related to Amazon Web Services, and the summary does not need to have customer service-related content:
{text}

The summary is:"""

chinses_chat_prompt="""你是一个聊天机器人，
{text}

摘要是:"""


api = invoke_url + '/langchain_processor_qa?query='

    
def get_chat(message, chat_history):

    session_id = ""
    #prompt="hi"
    url = api + message
    url += '&task=chat'
    language = "chinese"
    url += '&temperature=0.01'

    if len(session_id) > 0:
        url += ('&session_id='+session_id)

    if language == "english":
        url += '&language=english'
        url += ('&embedding_endpoint_name='+en_embedding_endpoint)
        url += ('&llm_embedding_name='+en_llm_endpoint)
        
    elif language == "chinese":
        url += '&language=chinese'
        url += ('&embedding_endpoint_name='+cn_embedding_endpoint)
        url += ('&llm_embedding_name='+cn_llm_endpoint)

    #if len(prompt) > 0:
    #    url += ('&prompt='+prompt)
    #else:
    #    if language == "english":
    #        url += ('&prompt='+english_summarize_prompt)
    #    elif language == "chinese":
    #        url += ('&prompt='+chinses_summarize_prompt)
    
    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print('result1:',result)
    
    answer = result['suggestion_answer']

    chat_history.append((message, answer))
    time.sleep(2)

    print("chathis",chat_history)

    # if language == 'english' and answer.find('The Question and Answer are:') > 0:
    #     answer=answer.split('The Question and Answer are:')[-1].strip()

    return "", chat_history

def get_answer(question,index,top_k,chat_history):
    
    score_type_checklist = ["query_answer_score"]
    #print(score_type_checklist)
    #print("index",index)
    language = "chinese"
    session_id = ""
    prompt=""
    search_engine = "OpenSearch"

    if len(question) > 0:
        url = api + question
    else:
        url = api + "hello"

    #task type: qa,chat
    task = 'qa'
    url += ('&task='+task)

    if language == "english":
        url += '&language=english'
        url += ('&embedding_endpoint_name='+en_embedding_endpoint)
        url += ('&llm_embedding_name='+en_llm_endpoint)
    elif language == "chinese":
        url += '&language=chinese'
        url += ('&embedding_endpoint_name='+cn_embedding_endpoint)
        url += ('&llm_embedding_name='+cn_llm_endpoint)
     
    elif language == "chinese-tc":
        url += '&language=chinese-tc'
        url += ('&embedding_endpoint_name='+cn_embedding_endpoint)
        url += ('&llm_embedding_name='+cn_llm_endpoint)
    
    if len(session_id) > 0:
        url += ('&session_id='+session_id)
    
        
    if len(prompt) > 0:
        url += ('&prompt='+prompt)

    if search_engine == "OpenSearch":
        url += ('&search_engine=opensearch')
        if len(index) > 0:
            url += ('&index='+index)
        else:
            if language.find("chinese") >= 0 and len(chinese_index) >0:
                url += ('&index='+chinese_index)
            elif language == "english" and len(english_index) >0:
                url += ('&index='+english_index)
    elif search_engine == "Kendra":
        url += ('&search_engine=kendra')
        if len(index) > 0:
            url += ('&kendra_index_id='+index)

    if int(top_k) > 0:
        url += ('&top_k='+str(top_k))

    for score_type in score_type_checklist:
        url += ('&cal_' + score_type +'=true')

    print("url:",url)

    now1 = datetime.now()#begin time
    response = requests.get(url)
    now2 = datetime.now()#endtime
    request_time = now2-now1
    print("request takes time:",request_time)

    result = response.text
    
    result = json.loads(result)
    print('result:',result)
    
    answer = result['suggestion_answer']
    source_list = []
    if 'source_list' in result.keys():
        source_list = result['source_list']
    
    print("answer:",answer)

    source_str = ""
    for i in range(len(source_list)):
        item = source_list[i]
        print('item:',item)
        _id = "num:" + str(item['id'])
        #source = "source:" + item['source']
        score = "score:" + str(item['score'])
        sentence = "sentence:" + item['sentence']
        paragraph = "paragraph:" + item['paragraph']
        source_str += (_id + "      " + score + '\n')
        # source_str += sentence + '\n'
        source_str += paragraph + '\n\n'
    
    confidence = ""
    query_docs_score = -1
    if 'query_docs_score' in result.keys():
        query_docs_score =  float(result['query_docs_score'])
    if query_docs_score >= 0:
        confidence += ("query_docs_score:" + str(query_docs_score) + '\n')

    query_answer_score = -1
    if 'query_answer_score' in result.keys():
        query_answer_score =  float(result['query_answer_score'])
    if query_answer_score >= 0:
        confidence += ("query_answer_score:" + str(query_answer_score) + '\n')

    answer_docs_score = -1
    if 'answer_docs_score' in result.keys():
        answer_docs_score =  float(result['answer_docs_score'])
    if answer_docs_score >= 0:
        confidence += ("answer_docs_score:" + str(answer_docs_score) + '\n')

    docs_list_overlap_score = -1
    if 'docs_list_overlap_score' in result.keys():
        docs_list_overlap_score =  float(result['docs_list_overlap_score'])
    if docs_list_overlap_score >= 0:
        confidence += ("docs_list_overlap_score:" + str(docs_list_overlap_score) + '\n')


    chat_history.append((question, answer))
    time.sleep(2)
    print("chathis",chat_history)
    # if language == 'english' and answer.find('The Question and Answer are:') > 0:
    #     answer=answer.split('The Question and Answer are:')[-1].strip()

    #return answer,confidence,source_str,url,request_time,chat_history
    return "", chat_history, source_str
    #return "",confidence,source_str,url,request_time,chat_history

#def upload_to_s3(file):
#    # Initialize a session using Amazon S3
#    s3 = boto3.client('s3', aws_access_key_id='',
#                      aws_secret_access_key='', region_name='us-east-1')
#
#    bucket_name = "sagemaker-us-east-1-955643200499"
#
#    full_path = file.name
#
#    # Extract the filename from the full path
#    file_name = os.path.basename(full_path)
#
#    try:
#        s3.upload_file(file.name, bucket_name, file_name)
#        return f"Successfully uploaded {file_name} to {bucket_name}"
#    except FileNotFoundError:
#        return "The file was not found"
#    except NoCredentialsError:
#        return "Credentials not available"
#    except PartialCredentialsError:
#        return "Incomplete credentials provided"
#    except Exception as e:
#        return str(e)


demo = gr.Blocks(title="AWS Intelligent Q&A Solution Guide")
with demo:
    gr.Markdown(
        "# <center>G1K LLM Demo"
    )

    with gr.Tabs():
#
#
    #    with gr.TabItem("Chatbot"):
    #        with gr.Row():
    #            with gr.Column():
    #                chatbot1 = gr.Chatbot().style(height=500)
    #                msg1 = gr.Textbox(show_label=False,placeholder="请输入提问内容，按回车提交")
    #                #chat_language_radio = gr.Radio(["chinese", "english"],value="chinese",label="Language")
    #                #chat_session_id_textbox = gr.Textbox(label="Session ID")
#
    #            #with gr.Column():
    #            #    session_id_textbox1 = gr.Textbox(label="Session ID")


       
        with gr.TabItem("RAG Chatbot"):

            with gr.Row():
                with gr.Column():
                    chatbot2 = gr.Chatbot().style(height=500)
                    msg2 = gr.Textbox(show_label=False,placeholder="请输入提问内容，按回车提交")

                    qa_output = [msg2, chatbot2]


                with gr.Column():
                    #session_id_textbox = gr.Textbox(label="Session ID")

                    #qa_language_radio = gr.Radio(["chinese"],value="chinese",label="Language")
                    #qa_prompt_textbox = gr.Textbox(label="Prompt( must include {context} and {question} )",placeholder=chinese_prompt,lines=8)
                    #qa_search_engine_radio = gr.Radio(["OpenSearch"],value="OpenSearch",label="Search engine")
                    qa_index_textbox = gr.Textbox(label="OpenSearch index", value="aws-faq-index", placeholder="aws-faq-index")
                    qa_top_k_slider = gr.Slider(label="Top_k of source text to LLM",value=1, minimum=1, maximum=4, step=1)
                    #score_type_checklist = gr.CheckboxGroup(["query_answer_score", "answer_docs_score","docs_list_overlap_score"],value=["query_answer_score"],label="Confidence score type")
                    qa_output = [msg2, chatbot2, gr.outputs.Textbox(label="Source")]


        #with gr.TabItem("Upload File"):
        #    with gr.Row():
        #        with gr.Column():
        #            file_upload = gr.inputs.File(label="Upload File")
        #            upload_button = gr.Button(label="Upload")
        #            upload_status = gr.Label(label="Upload Status")
        #        with gr.Column():
        #            upload_result = gr.Label(label="Upload Result")

    #msg1.submit(get_chat, 
    #           inputs=[msg1, 
    #                    #session_id_textbox1, 
    #                    chatbot1], 
    #           outputs=[msg1, chatbot1]
    #           )

    msg2.submit(get_answer, 
               inputs=[msg2,
                       qa_index_textbox,
                       qa_top_k_slider,
                       chatbot2], 
               outputs=qa_output
               )
    
    #upload_button.click(upload_to_s3, 
    #                    inputs=file_upload,
    #                    outputs=upload_result
    #                    )

    

# demo.launch()
demo.launch(share=True)
