#!/usr/bin/env python3
"""
Скрипт для миграции документов из Craft в Obsidian через Second Brain
Сохраняет структуру папок и содержимое документов
"""

import os
import sys
import json
import requests
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import time

# Конфигурация Craft API
CRAFT_API_BASE = "https://connect.craft.do/links/IBp0v0wNdwe/api/v1"
CRAFT_API_KEY = "pdk_b798a63f-18cd-c474-e89f-602359fb5b29"

# Конфигурация Second Brain API
SECOND_BRAIN_API = os.getenv("SECOND_BRAIN_API", "http://localhost:8000")
NOTES_API_TOKEN = os.getenv("NOTES_API_TOKEN", "")

# Директория для экспорта (локальное хранилище)
EXPORT_DIR = Path("./craft_export")

class CraftClient:
    """Клиент для работы с Craft API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = CRAFT_API_BASE
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_folders(self) -> List[Dict]:
        """Получить структуру папок"""
        response = requests.get(
            f"{self.base_url}/folders",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json().get("items", [])
    
    def get_documents(self, location: Optional[str] = None, folder_id: Optional[str] = None) -> List[Dict]:
        """Получить список документов"""
        params = {"fetchMetadata": "true"}
        if location:
            params["location"] = location
        if folder_id:
            params["folderId"] = folder_id
        
        response = requests.get(
            f"{self.base_url}/documents",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json().get("items", [])
    
    def get_document_content(self, document_id: str) -> Dict:
        """Получить содержимое документа"""
        response = requests.get(
            f"{self.base_url}/blocks",
            headers=self.headers,
            params={
                "id": document_id,
                "maxDepth": -1,
                "fetchMetadata": "true"
            }
        )
        response.raise_for_status()
        return response.json()


class MarkdownConverter:
    """Конвертер Craft markdown в Obsidian markdown"""
    
    @staticmethod
    def clean_markdown(content: str) -> str:
        """Очистить markdown от специфичных тегов Craft"""
        # Удалить теги <page></page>
        content = re.sub(r'<page>(.*?)</page>', r'\1', content, flags=re.DOTALL)
        
        # Удалить другие служебные теги
        content = re.sub(r'<card>(.*?)</card>', r'\1', content, flags=re.DOTALL)
        
        # Нормализовать переводы строк
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
    
    @staticmethod
    def block_to_markdown(block: Dict, level: int = 0) -> str:
        """Конвертировать блок Craft в markdown"""
        markdown_parts = []
        
        # Получить markdown текущего блока
        if "markdown" in block:
            md = block["markdown"]
            markdown_parts.append(md)
        
        # Обработать дочерние блоки
        if "content" in block and isinstance(block["content"], list):
            for child in block["content"]:
                child_md = MarkdownConverter.block_to_markdown(child, level + 1)
                if child_md:
                    markdown_parts.append(child_md)
        
        result = "\n\n".join(markdown_parts)
        return MarkdownConverter.clean_markdown(result)


class ObsidianExporter:
    """Экспортер в локальную файловую систему (Obsidian vault)"""
    
    def __init__(self, export_dir: Path):
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def save_document(self, path: str, title: str, content: str, metadata: Dict):
        """Сохранить документ как .md файл"""
        # Создать путь к файлу
        full_path = self.export_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Создать frontmatter для Obsidian
        frontmatter = [
            "---",
            f"title: {title}",
            f"source: Craft",
            f"imported: {datetime.now().isoformat()}",
        ]
        
        if metadata.get("createdAt"):
            frontmatter.append(f"created: {metadata['createdAt']}")
        if metadata.get("lastModifiedAt"):
            frontmatter.append(f"modified: {metadata['lastModifiedAt']}")
        
        frontmatter.append("---")
        frontmatter.append("")
        
        # Записать файл
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(frontmatter))
            f.write("\n")
            f.write(content)
        
        print(f"✓ Saved: {path}")


class CraftMigrator:
    """Основной класс для миграции"""
    
    def __init__(self):
        self.craft = CraftClient(CRAFT_API_KEY)
        self.exporter = ObsidianExporter(EXPORT_DIR)
        self.stats = {
            "folders": 0,
            "documents": 0,
            "errors": 0
        }
    
    def process_folder(self, folder: Dict, parent_path: str = "") -> None:
        """Обработать папку рекурсивно"""
        folder_name = folder.get("name", "Unnamed")
        folder_id = folder.get("id")
        
        # Игнорировать служебные локации
        if folder_id in ["trash", "templates"]:
            print(f"⊘ Skipping: {folder_name}")
            return
        
        # Определить путь к папке
        if folder_id in ["unsorted", "daily_notes"]:
            folder_path = parent_path
            location = folder_id
            use_folder_id = False
        else:
            # Безопасное имя для файловой системы
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', folder_name)
            folder_path = os.path.join(parent_path, safe_name) if parent_path else safe_name
            location = None
            use_folder_id = True
        
        print(f"\n📁 Processing folder: {folder_name} ({folder.get('documentCount', 0)} docs)")
        self.stats["folders"] += 1
        
        # Получить документы в этой папке
        try:
            if use_folder_id:
                documents = self.craft.get_documents(folder_id=folder_id)
            else:
                documents = self.craft.get_documents(location=location)
            
            # Обработать каждый документ
            for doc in documents:
                self.process_document(doc, folder_path)
                time.sleep(0.5)  # Небольшая задержка между запросами
        
        except Exception as e:
            print(f"✗ Error processing folder {folder_name}: {e}")
            self.stats["errors"] += 1
        
        # Рекурсивно обработать подпапки
        subfolders = folder.get("folders", [])
        for subfolder in subfolders:
            self.process_folder(subfolder, folder_path)
    
    def process_document(self, doc: Dict, folder_path: str) -> None:
        """Обработать один документ"""
        doc_id = doc.get("id")
        title = doc.get("title", "Untitled")
        
        # Безопасное имя файла
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        file_path = os.path.join(folder_path, f"{safe_title}.md") if folder_path else f"{safe_title}.md"
        
        print(f"  📄 Processing: {title}")
        
        try:
            # Получить содержимое
            content_data = self.craft.get_document_content(doc_id)
            
            # Конвертировать в markdown
            markdown = MarkdownConverter.block_to_markdown(content_data)
            
            # Сохранить
            metadata = {
                "createdAt": doc.get("createdAt"),
                "lastModifiedAt": doc.get("lastModifiedAt"),
                "dailyNoteDate": doc.get("dailyNoteDate")
            }
            
            self.exporter.save_document(file_path, title, markdown, metadata)
            self.stats["documents"] += 1
            
        except Exception as e:
            print(f"  ✗ Error processing document {title}: {e}")
            self.stats["errors"] += 1
    
    def migrate(self) -> None:
        """Запустить миграцию"""
        print("=" * 60)
        print("Craft → Obsidian Migration")
        print("=" * 60)
        print(f"Export directory: {EXPORT_DIR.absolute()}")
        print()
        
        try:
            # Получить структуру
            print("Fetching folder structure...")
            folders = self.craft.get_folders()
            print(f"Found {len(folders)} top-level folders\n")
            
            # Обработать каждую папку
            for folder in folders:
                self.process_folder(folder)
            
            # Итоговая статистика
            print("\n" + "=" * 60)
            print("Migration Complete!")
            print("=" * 60)
            print(f"Folders processed: {self.stats['folders']}")
            print(f"Documents migrated: {self.stats['documents']}")
            print(f"Errors: {self.stats['errors']}")
            print(f"\nFiles saved to: {EXPORT_DIR.absolute()}")
            print("\nNext steps:")
            print("1. Review the exported files")
            print("2. Copy them to your Obsidian vault")
            print("3. Or sync via Obsidian LiveSync")
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            sys.exit(1)


def main():
    """Главная функция"""
    # Проверить API ключ
    if not CRAFT_API_KEY or CRAFT_API_KEY.startswith("your"):
        print("Error: Please set CRAFT_API_KEY")
        sys.exit(1)
    
    # Запустить миграцию
    migrator = CraftMigrator()
    migrator.migrate()


if __name__ == "__main__":
    main()
