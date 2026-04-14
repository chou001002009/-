import streamlit as st
import google.generativeai as genai
import time
import os

# ==========================================
# 1. 頻道專屬設定
# ==========================================
VIDEO_SERIES = ["送你營養吃", "阿環格格出遊去", "阿環格格花錢去", "Vlog", "其他"]

SYSTEM_INSTRUCTION = """你現在是一位專業的 YouTube 影片逐字稿聽打與校正助理，專門處理「Sunny營養師」頻道的內容。
你的任務是：
1. 接收「音軌檔案」或「原始逐字稿文字」。
2. 根據以下「絕對校正規則」進行修正：
   - 【人物】：保留安媽、阿嬤、阿環、Sunny等稱謂，不要強制統一。
   - 【台語】：錯誤國語同音字還原為台語漢字（如：哩賀、歹勢、安捏）。
   - 【專有名詞】：水氣->牙齒、好有嚇->比較划算、各美心->鉻鎂鋅、糖流到臉->糖尿病、一瓶->一邊。
   - 【格式】：每行絕對不可超過 16 個字，不需加上任何標點符號。
   - 【贅字】：只刪除「啊、呢、嗯、喔、耶、嘛」這六個。
   - 【副詞】：一律使用「蠻」，不可使用「滿」。

請直接輸出校正後的純文字結果，不要有任何額外的解釋。"""

# ==========================================
# 2. 核心處理邏輯
# ==========================================
def process_content(api_key, series, uploaded_file=None, manual_text=None):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # 模式 A：上傳了檔案（音軌或文字檔）
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        # 處理文字檔 (.txt)
        if file_ext == 'txt':
            content = uploaded_file.read().decode("utf-8")
            prompt = f"影片系列：{series}\n請校正以下逐字稿文字：\n\n{content}"
            response = model.generate_content([SYSTEM_INSTRUCTION, prompt])
            return response.text
        
        # 處理音軌/影片檔 (.mp3, .m4a, .wav, .mp4, .mov)
        else:
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.info(f"正在傳輸音軌/影音檔 ({uploaded_file.name})...")
            # 上傳檔案至 Google AI 伺服器
            audio_file = genai.upload_file(path=temp_path)
            
            # 等待檔案分析完成
            while audio_file.state.name == "PROCESSING":
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            
            prompt = f"這是「{series}」系列的影片音軌，請聽取內容並依照規則生成校正後的純文字逐字稿。"
            response = model.generate_content(
                [audio_file, "\n\n", SYSTEM_INSTRUCTION, prompt],
                request_options={"timeout": 600}
            )
            
            # 清除暫存並刪除雲端檔案
            os.remove(temp_path)
            genai.delete_file(audio_file.name)
            return response.text

    # 模式 B：手動貼上文字
    elif manual_text:
        prompt = f"影片系列：{series}\n請校正以下逐字稿文字：\n\n{manual_text}"
        response = model.generate_content([SYSTEM_INSTRUCTION, prompt])
        return response.text
    
    return "請提供檔案或輸入文字。"

# ==========================================
# 3. Streamlit 介面
# ==========================================
def main():
    st.set_page_config(page_title="Sunny 影音/文字校正器", layout="wide", page_icon="🎙️")
    st.title("🎙️ Sunny 營養師：影音轉文字與校正工具")

    with st.sidebar:
        st.header("🔑 設定")
        api_key = st.text_input("Gemini API Key", type="password")
        series = st.selectbox("影片系列", VIDEO_SERIES)
        st.divider()
        st.write("💡 提示：上傳 **MP3** 或 **M4A** 音檔速度最快，且精準度與影片相同。")

    col_in, col_out = st.columns(2)

    with col_in:
        st.subheader("📥 輸入內容")
        # 增加音訊格式支援
        uploaded_file = st.file_uploader(
            "上傳音軌、影片或文字檔", 
            type=['mp3', 'm4a', 'wav', 'mp4', 'mov', 'txt']
        )
        
        st.write("--- 或 ---")
        manual_text = st.text_area("在此貼上原始文字：", height=300, placeholder="若已有剪映辨識好的文字，可直接貼在此處進行校正...")

    with col_out:
        st.subheader("📤 校正結果")
        if st.button("🚀 開始執行", use_container_width=True):
            if not api_key:
                st.error("請先輸入 API Key")
            elif not uploaded_file and not manual_text:
                st.warning("請提供檔案或貼入文字")
            else:
                with st.spinner("AI 正在分析與校正中..."):
                    try:
                        result = process_content(api_key, series, uploaded_file, manual_text)
                        st.text_area("校正完成內容：", result, height=500)
                        st.success("校正完畢！可直接複製到剪映。")
                    except Exception as e:
                        st.error(f"發生錯誤：{e}")

if __name__ == "__main__":
    main()
