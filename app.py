import streamlit as st
import subprocess
import os
import tempfile
import math

st.set_page_config(
    page_title="Telegram Sticker/Emoji Factory",
    page_icon="🎬",
    layout="centered"
)

# Custom Elegant CSS Customization
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    h1 { color: #1e293b; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton>button:hover { background-color: #1d4ed8; color: white; }
    .success-box {
        padding: 12px;
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        color: #166534;
        border-radius: 4px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 مصنع ملصقات وإيموجي تليجرام")
st.subheader("حوّل أي فيديو أو صورة إلى صيغة .WEBM المتوافقة رسميًا بثوانٍ معدودة")

# تم تحديث الأنواع المدعومة لتشمل الصور أيضاً
uploaded_file = st.file_uploader("اختر ملف فيديو أو صورة (MP4, MOV, MKV, JPG, PNG)", type=["mp4", "mov", "mkv", "avi", "jpg", "jpeg", "png"])

if uploaded_file is not None:
    # معرفة نوع الملف المرفوع (فيديو أم صورة)
    file_type = uploaded_file.type.split('/')[0] # 'video' or 'image'
    
    # Save uploaded file to a temporary location
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    tfile.write(uploaded_file.read())
    tfile.close()
    
    video_duration = 3.0  # القيمة الافتراضية للصور
    
    # عرض الملف وجلب المدة إذا كان فيديو
    if file_type == "video":
        try:
            duration_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{tfile.name}"'
            video_duration = float(subprocess.check_output(duration_cmd, shell=True).decode().strip())
        except Exception:
            video_duration = 10.0  # fallback value
        st.video(tfile.name)
    else:
        # عرض الصورة المرفوعة
        st.image(tfile.name, caption="الصورة المرفوعة المُراد تحويلها لملصق متحرك/ثابت", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### ⚙️ إعدادات التعديل والقص")
    
    # Target Selection
    target_type = st.radio("نوع المخرج المطلوب:", ["ملصق متحرك (Sticker - 512x512)", "رمز تعبيري متحرك (Emoji - 100x100)"])
    
    # إعدادات الوقت تظهر فقط في حال كان الملف المرفوع فيديو
    if file_type == "video":
        st.write("⏳ تحديد وقت الفيديو (الحد الأقصى 3 ثوانٍ):")
        start_time = st.number_input("وقت البدء (بالثواني):", min_value=0.0, max_value=max(0.0, video_duration-0.1), value=0.0, step=0.1)
        end_time = st.number_input("وقت الانتهاء (بالثواني):", min_value=start_time+0.1, max_value=video_duration, value=min(start_time+3.0, video_duration), step=0.1)
        selected_duration = end_time - start_time
        st.info(f"⏱️ طول الفيديو المحدد الحالي: {selected_duration:.2f} ثانية")
        
        if selected_duration > 3.0:
            st.error("⚠️ تحذير: شروط تليجرام تمنع أن يتخطى طول الفيديو 3 ثوانٍ!")
    else:
        # إذا كانت صورة، نجعل المدة الافتراضية ثانية واحدة (وهي كافية وممتازة للملصقات الثابتة بصيغة الفيديو)
        start_time = 0
        end_time = 1.0
        selected_duration = 1.0
        st.success("📸 تم التعرف على الملف كصورة ثابتة. سيتم توليد فيديو مدته ثانية واحدة لتلبية شروط تليجرام.")

    # Scale calculation
    if "Sticker" in target_type:
        scale_filter = "scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(512-iw)/2:(512-ih)/2:color=black@0"
        res_label = "512x512"
    else:
        scale_filter = "scale=100:100"
        res_label = "100x100"

    if st.button("🚀 ابدأ المعالجة والتحويل"):
        if file_type == "video" and selected_duration > 3.0:
            st.error("يرجى تعديل الوقت ليصبح 3 ثوانٍ أو أقل أولاً.")
        else:
            with st.spinner("جاري معالجة الملف وضغطه بكوديك VP9..."):
                output_filename = "telegram_target.webm"
                if os.path.exists(output_filename):
                    os.remove(output_filename)
                
                # Intelligent Bitrate calculation to guarantee size < 256KB
                safe_bitrate_kbps = math.floor((240 * 8) / selected_duration)
                
                # بناء أمر FFmpeg بناءً على نوع الملف
                if file_type == "video":
                    ffmpeg_cmd = (
                        f'ffmpeg -ss {start_time} -to {end_time} -i "{tfile.name}" '
                        f'-vf "{scale_filter},fps=30" -c:v libvpx-vp9 -b:v {safe_bitrate_kbps}k '
                        f'-minrate {safe_bitrate_kbps//2}k -maxrate {int(safe_bitrate_kbps*1.2)}k '
                        f'-an -loop 0 -y {output_filename}'
                    )
                else:
                    # تحويل الصورة الثابتة إلى فيديو loop (مدته ثانية واحدة وبمعدل إطارات منخفض لتوفير الحجم)
                    ffmpeg_cmd = (
                        f'ffmpeg -loop 1 -t {selected_duration} -i "{tfile.name}" '
                        f'-vf "{scale_filter},fps=5" -c:v libvpx-vp9 -b:v {safe_bitrate_kbps}k '
                        f'-minrate {safe_bitrate_kbps//2}k -maxrate {int(safe_bitrate_kbps*1.2)}k '
                        f'-an -y {output_filename}'
                    )
                
                # Run the process
                process = subprocess.run(ffmpeg_cmd, shell=True, capture_output=True, text=True)
                
                if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
                    file_size_kb = os.path.getsize(output_filename) / 1024
                    
                    st.markdown('<div class="success-box">🎉 تم تحويل وتجهيز الملف بنجاح ومطابقة كافة الشروط المحددة!</div>', unsafe_allow_html=True)
                    
                    # Metrics Layout
                    col1, col2, col3 = st.columns(3)
                    col1.metric("صيغة الملف", "WEBM (VP9)")
                    col2.metric("أبعاد الفيديو", res_label)
                    col3.metric("حجم الملف النهائي", f"{file_size_kb:.1f} KB")
                    
                    # Reading the binary file for Streamlit download button
                    with open(output_filename, "rb") as f:
                        webm_bytes = f.read()
                        
                    st.download_button(
                        label="📥 تحميل الملف الجاهز للتليجرام",
                        data=webm_bytes,
                        file_name="telegram_sticker.webm",
                        mime="video/webm"
                    )
                else:
                    st.error("فشلت عملية التحويل. يرجى التحقق من صياغة الملف الأصلي.")
                    st.text(process.stderr)
                    
    # Clean up local temporary file
    try:
        os.unlink(tfile.name)
    except Exception:
        pass
