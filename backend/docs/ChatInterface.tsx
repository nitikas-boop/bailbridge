"use client";

import React, { useEffect, useState, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

/**
 * BailBridge — Chat Interface Component (Phase 2 Snippet)
 * 
 * Connects to the Socket.IO bridge, handles message history, 
 * and displays real-time agent updates and typing indicators.
 */
interface Message {
  text: string;
  sender: 'user' | 'agent' | 'ai';
  timestamp: string;
}

export default function ChatInterface({ caseId }: { caseId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [bailPdfUrl, setBailPdfUrl] = useState<string | null>(null);
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // ... (socket init remains same)
    const socket = io("http://localhost:8000", {
      path: "/ws/socket.io",
      transports: ["websocket"],
    });
    socketRef.current = socket;

    socket.on("case_update", (data: any) => {
      // If we get a bail_pdf_ready event, update the URL
      if (data.status === "bail_pdf_ready" && data.bail_pdf_url) {
        setBailPdfUrl(data.bail_pdf_url);
      }
      
      setMessages((prev: Message[]) => [...prev, {
        text: `[Update] ${data.message}`,
        sender: 'agent',
        timestamp: data.timestamp || new Date().toISOString()
      }]);
    });
    
    // ... (rest of listeners)
    return () => { socket.disconnect(); };
  }, [caseId]);

  const handleSendMessage = () => {
    if (!inputText.trim() || !socketRef.current) return;

    const payload = {
      case_id: caseId,
      text: inputText,
      sender_id: "frontend_user"
    };

    socketRef.current.emit("defendant_message", payload);
    
    setMessages((prev: Message[]) => [...prev, {
      text: inputText,
      sender: 'user',
      timestamp: new Date().toISOString()
    }]);
    
    setInputText('');
  };

  return (
    <div className="flex flex-col h-[700px] w-full max-w-2xl mx-auto bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-800 font-sans text-slate-100">
      {/* Header with Download Button */}
      <div className="p-4 bg-slate-800/50 backdrop-blur-md border-b border-slate-700 flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg">Legal Case Chat</h2>
          <p className="text-xs text-slate-400">Reference: {caseId}</p>
        </div>
        <div className="flex items-center gap-3">
          {bailPdfUrl && (
            <a 
              href={bailPdfUrl} 
              target="_blank" 
              className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-2"
            >
              <span>Download Bail Draft</span>
            </a>
          )}
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
            <span className="text-xs font-medium text-slate-300">Live</span>
          </div>
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-2xl text-sm shadow-sm ${
              msg.sender === 'user' 
                ? 'bg-indigo-600 text-white rounded-br-none' 
                : msg.sender === 'ai'
                ? 'bg-slate-800 text-slate-200 border border-slate-700 rounded-bl-none'
                : 'bg-amber-900/40 text-amber-100 border border-amber-800/50 rounded-bl-none'
            }`}>
              {msg.text}
              <span className="block text-[10px] mt-1 opacity-50 text-right">
                {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-slate-800 p-3 rounded-2xl rounded-bl-none flex gap-1 items-center">
              <span className="w-1 h-1 bg-slate-400 rounded-full animate-bounce" />
              <span className="w-1 h-1 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              <span className="w-1 h-1 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]" />
            </div>
          </div>
        )}
      </div>

      {/* Input Area + Evidence Upload */}
      <div className="p-4 bg-slate-800/30 border-t border-slate-700 space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Provide case details..."
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button onClick={handleSendMessage} className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 rounded-xl text-sm font-semibold">
            Send
          </button>
        </div>
        <div className="flex justify-start">
          <button className="text-[10px] text-slate-400 hover:text-indigo-400 flex items-center gap-1 transition-colors">
            <span>📎 Upload Evidence (ID Proof / FIR)</span>
          </button>
        </div>
      </div>
    </div>
  );
}
