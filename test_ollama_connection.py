"""测试 Ollama 连接的脚本"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ollama_client import AIClient

def test_ollama():
    print("=" * 60)
    print("Ollama 连接测试")
    print("=" * 60)
    
    # 创建客户端
    client = AIClient(
        provider="ollama",
        base_url="http://localhost:11434",
        model="qwen2.5:7b"
    )
    
    print(f"\n配置信息:")
    print(f"  - 提供商: {client.provider}")
    print(f"  - URL: {client.base_url}")
    print(f"  - 模型: {client.model}")
    
    # 测试消息
    messages = [
        {"role": "system", "content": "你是一个友好的助手"},
        {"role": "user", "content": "你好，请简单回复"}
    ]
    
    print(f"\n发送测试消息...")
    print(f"  - 消息数: {len(messages)}")
    
    try:
        print("\n正在连接 Ollama...")
        reply = client.chat(messages, timeout=30)
        
        print("\n✅ 成功！")
        print(f"\n回复内容:")
        print("-" * 60)
        print(reply)
        print("-" * 60)
        print(f"\n回复长度: {len(reply)} 字符")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 失败！")
        print(f"\n错误类型: {type(e).__name__}")
        print(f"错误信息:")
        print("-" * 60)
        print(str(e))
        print("-" * 60)
        
        import traceback
        print("\n详细堆栈:")
        traceback.print_exc()
        
        return False

if __name__ == "__main__":
    success = test_ollama()
    sys.exit(0 if success else 1)
