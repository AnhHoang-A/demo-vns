import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import re
import google.generativeai as genai

class AITextFixerMax(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Trợ lý AI Soát lỗi Tiếng Việt - Tự động hóa Toàn diện")
        self.geometry("950x800")
        self.configure(padx=20, pady=20)
        
        # === CẤU HÌNH API KEY TẠI ĐÂY ===
        self.api_key = "AIzaSyD_j-6UcyxkU8FQlReaYSsMV89ZWsnr7VA" 
        
        # Biến lưu trữ danh sách các widget lỗi để xử lý hàng loạt
        self.error_widgets = []
        
        self.setup_ui()

    def setup_ui(self):
        # --- Khung Nhập Văn Bản ---
        ttk.Label(self, text="Nhập văn bản cần kiểm tra (Dán đoạn văn lỗi vào đây):", font=("Arial", 11, "bold")).pack(anchor="w")
        self.input_text = scrolledtext.ScrolledText(self, height=12, font=("Arial", 13), undo=True)
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # --- Nút Chức Năng Chính ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.btn_check = ttk.Button(btn_frame, text="🤖 Nhờ AI Phân tích Lỗi", command=self.start_ai_analysis)
        self.btn_check.pack(side=tk.LEFT, padx=5)
        
        self.btn_normalize = ttk.Button(btn_frame, text="✨ Chuẩn hóa Dấu câu & Khoảng trắng", command=self.normalize_text)
        self.btn_normalize.pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(btn_frame, text="", font=("Arial", 10, "italic"))
        self.status_label.pack(side=tk.LEFT, padx=15)

        # --- Khung Gợi Ý Sửa Lỗi ---
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Label(header_frame, text="AI Đề xuất sửa:", font=("Arial", 11, "bold"), foreground="red").pack(side=tk.LEFT)
        
        # Nút SỬA HÀNG LOẠT (Ban đầu bị ẩn/vô hiệu hóa)
        self.btn_fix_all = tk.Button(header_frame, text="⚡ Sửa Toàn bộ Lỗi", bg="#2196F3", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED, command=self.apply_all_fixes)
        self.btn_fix_all.pack(side=tk.RIGHT)

        # Khu vực danh sách cuộn
        self.canvas = tk.Canvas(self, height=250, bg="#f8f9fa", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # ================= CÔNG CỤ CHUẨN HÓA BỀ MẶT =================
    def normalize_text(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text: return
        
        # 1. Biến nhiều khoảng trắng thành 1 khoảng trắng (Sửa "tôi    là")
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 2. Xóa khoảng trắng TRƯỚC dấu câu (Sửa "bạn , tôi" ➔ "bạn, tôi")
        text = re.sub(r'\s+([.,?!:;])', r'\1', text)
        
        # 3. Thêm khoảng trắng SAU dấu câu nếu đang dính liền (Sửa "bạn,tôi" ➔ "bạn, tôi")
        text = re.sub(r'([.,?!:;])(?=[^\s])', r'\1 ', text)
        
        # 4. Viết hoa chữ cái đầu tiên của câu
        sentences = re.split(r'(?<=[.!?]) +', text)
        text = ' '.join([s.capitalize() if s else '' for s in sentences])
        
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert(tk.END, text)
        self.status_label.config(text="✅ Đã chuẩn hóa khoảng trắng và dấu câu!", foreground="green")

    # ================= AI XỬ LÝ LỖI SÂU =================
    def start_ai_analysis(self):
        text = self.input_text.get("1.0", tk.END).strip()
        if not text: return

        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.error_widgets.clear() # Xóa bộ nhớ lỗi cũ
        self.btn_fix_all.config(state=tk.DISABLED, bg="#cccccc") # Tắt nút sửa hàng loạt
        
        self.btn_check.config(state=tk.DISABLED)
        self.status_label.config(text="⏳ AI đang đọc và phân tích...", foreground="blue")
        
        threading.Thread(target=self.call_ai_api, args=(text,), daemon=True).start()

    def call_ai_api(self, text):
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Ép AI tìm thêm lỗi "Dính chữ"
            prompt = f"""
            Bạn là chuyên gia ngôn ngữ. Tìm lỗi: chính tả, teencode, ngữ pháp, DÍNH CHỮ, và lỗi khác không nhận diện đc chữ (ví dụ: 'siêunhân' phải tách thành 'siêu nhân')(ví dụ:'ă ndi  jass' thành lỗi sai) trong đoạn: "{text}".
            Trả về duy nhất mảng JSON: [{{"sai": "...", "dung": "...", "loai": "..."}}]
            Nếu không có lỗi, trả về mảng rỗng [].
            """
            
            response = model.generate_content(prompt)
            clean_json = re.sub(r'```json|```', '', response.text).strip()
            errors = json.loads(clean_json)
            
            self.after(0, self.display_results, errors)
        except Exception as e:
            self.after(0, self.display_error, str(e))

    def display_results(self, errors):
        self.btn_check.config(state=tk.NORMAL)
        
        if not errors:
            self.status_label.config(text="✅ Tuyệt vời! Không phát hiện lỗi nào.", foreground="green")
            ttk.Label(self.scrollable_frame, text="✨ Văn bản của bạn đã rất chuẩn xác!", font=("Arial", 11)).pack(pady=20)
            return

        self.status_label.config(text=f"Phát hiện {len(errors)} lỗi cần xử lý.", foreground="red")
        self.btn_fix_all.config(state=tk.NORMAL, bg="#2196F3") # Bật nút sửa hàng loạt
        
        for err in errors:
            self.create_error_row(err)

    def create_error_row(self, err):
        sai, dung, loai = err.get("sai"), err.get("dung"), err.get("loai")
        
        row = tk.Frame(self.scrollable_frame, bg="#fff", pady=8, padx=10, highlightbackground="#e0e0e0", highlightthickness=1)
        row.pack(fill=tk.X, padx=10, pady=4)
        
        lbl = tk.Label(row, text=f"[{loai}] '{sai}' ➔ '{dung}'", font=("Arial", 11), bg="#fff", fg="#333")
        lbl.pack(side=tk.LEFT)
        
        btn = tk.Button(row, text="🛠️ Sửa", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), relief="flat", padx=10)
        btn.config(command=lambda s=sai, d=dung, r=row, l=lbl, b=btn: self.apply_single_fix(s, d, r, l, b))
        btn.pack(side=tk.RIGHT)
        
        # Lưu lại để dùng cho chức năng "Sửa Hàng Loạt"
        self.error_widgets.append({
            "wrong": sai, "correct": dung, "row": row, "label": lbl, "btn": btn, "fixed": False
        })

    # ================= CÁC HÀM ÁP DỤNG SỬA LỖI =================
    def apply_single_fix(self, wrong, correct, row_widget, label_widget, button_widget):
        text = self.input_text.get("1.0", tk.END)
        pattern = re.compile(r'(?<!\w)' + re.escape(wrong) + r'(?!\w)', re.IGNORECASE)
        
        new_text = pattern.sub(correct, text, count=1)
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert(tk.END, new_text.rstrip('\n'))
        
        # Làm mờ UI
        self.dim_widget(row_widget, label_widget, button_widget, wrong)
        
        # Đánh dấu đã sửa trong danh sách để lúc bấm Sửa Hàng Loạt nó bỏ qua
        for item in self.error_widgets:
            if item["wrong"] == wrong and item["row"] == row_widget:
                item["fixed"] = True

    def apply_all_fixes(self):
        text = self.input_text.get("1.0", tk.END)
        
        # Duyệt qua toàn bộ lỗi chưa sửa
        for item in self.error_widgets:
            if not item["fixed"]:
                wrong = item["wrong"]
                correct = item["correct"]
                pattern = re.compile(r'(?<!\w)' + re.escape(wrong) + r'(?!\w)', re.IGNORECASE)
                text = pattern.sub(correct, text, count=1)
                
                # Làm mờ UI hàng loạt
                self.dim_widget(item["row"], item["label"], item["btn"], wrong)
                item["fixed"] = True
                
        # Cập nhật ô văn bản 1 lần duy nhất
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert(tk.END, text.rstrip('\n'))
        
        # Tắt nút Sửa Hàng Loạt
        self.btn_fix_all.config(state=tk.DISABLED, bg="#cccccc")
        self.status_label.config(text="✅ Đã sửa đổi toàn bộ các đề xuất!", foreground="green")

    def dim_widget(self, row_widget, label_widget, button_widget, wrong_word):
        """Hàm dùng chung để làm mờ các dòng báo lỗi sau khi đã sửa xong"""
        row_widget.config(bg="#f0f0f0", highlightbackground="#cccccc")
        label_widget.config(bg="#f0f0f0", fg="#aaaaaa", text=f"✓ Đã sửa: '{wrong_word}'")
        button_widget.config(state=tk.DISABLED, bg="#cccccc", text="Đã xong")

    def display_error(self, msg):
        self.btn_check.config(state=tk.NORMAL)
        self.status_label.config(text="❌ Lỗi kết nối AI", foreground="red")
        messagebox.showerror("Lỗi", msg)

if __name__ == "__main__":
    app = AITextFixerMax()
    app.mainloop()