import sqlite3
import os

DB_PATH = "bot_database.db"

def init_db():
    """Khởi tạo cơ sở dữ liệu SQLite"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Bảng cấu hình tổng hợp cho toàn bộ Server
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                -- Nhật ký (Logs)
                server_logs_id INTEGER,
                member_logs_id INTEGER,
                message_logs_id INTEGER,
                mod_logs_id INTEGER,
                ticket_logs_id INTEGER,
                -- Chào mừng & Tạm biệt
                welcome_channel_id INTEGER,
                goodbye_channel_id INTEGER,
                auto_role_id INTEGER,
                -- Hệ thống Ticket
                ticket_category_id INTEGER,
                ticket_support_role_id TEXT
            )
        """)
        conn.commit()
    print("💾 [Database] Đã đồng bộ bảng cấu hình tổng hợp thành công.")

def set_server_setting(guild_id: int, key: str, value: int):
    """Lưu/Cập nhật linh hoạt 1 giá trị cấu hình theo Tên Cột"""
    valid_keys = [
        "server_logs_id", "member_logs_id", "message_logs_id", 
        "mod_logs_id", "ticket_logs_id", "welcome_channel_id", 
        "goodbye_channel_id", "auto_role_id", "ticket_category_id", 
        "ticket_support_role_id"
    ]
    if key not in valid_keys:
        return False

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO server_config (guild_id, {key})
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET {key} = excluded.{key}
        """, (guild_id, value))
        conn.commit()
    return True

def get_guild_config(guild_id: int) -> dict:
    """Lấy toàn bộ cấu hình của một máy chủ"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM server_config WHERE guild_id = ?", (guild_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}