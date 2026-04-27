# {計劃書標題}

## 計劃書檔名
- plan_{title_name}.md

## 目標
1. 說明本次修改要解決的核心問題。
2. 說明解決方案。

## 範圍與限制
- 只修改：{目標 .grc 檔案}
- 不修改：{明確列出不動的檔案或模組}

## 現況錨點
- TX 關鍵鏈路：
- RX 關鍵鏈路：

## 設計總覽
- 說明修改後的資料流、封包切界與同步策略。

## Phase 1：變數與基礎定義
### 新增或修改項目
- 變數 A
- 變數 B

### 參數明細（完整欄位）
#### Block: {block_name} ({block_id})
| 欄位名稱 | 計劃值 |
|---|---|
|  |  |

### Python block 程式碼（若本 phase 修改 Python block）
#### Block: {block_name} ({block_id})
- 原始碼來源：{.grc Embedded Python Block / 外部 Python 檔案路徑}

#### 程式碼差異
{說明此區塊修改目的}

修改前（L{old_start}-L{old_end}）：
```python
{修改前程式碼}
```

修改後（L{new_start}-L{new_end}，可直接複製）：
```python
{修改後程式碼}
```

### 連線調整
- 移除：
- 新增：

## Phase 2：TX 鏈路調整
### 新增或修改 block
- {block_name}

### 參數明細（完整欄位）
#### Block: {block_name} ({block_id})
| 欄位名稱 | 計劃值 |
|---|---|
|  |  |

### Python block 程式碼（若本 phase 修改 Python block）
#### Block: {block_name} ({block_id})
- 原始碼來源：{.grc Embedded Python Block / 外部 Python 檔案路徑}
- 套用方式：以「完整替換程式碼」整段取代該 block 原始碼；「程式碼差異」僅供審閱。

#### 行號與變更摘要
| 原始行號 | 新版行號 | 變更說明 |
|---|---|---|
| L{start}-L{end} | L{start}-L{end} | {說明此區塊修改目的} |

#### 程式碼差異
修改前（L{old_start}-L{old_end}）：
```python
{修改前程式碼}
```

修改後（L{new_start}-L{new_end}，可直接複製）：
```python
{修改後程式碼}
```

### 連線調整
- 移除：
- 新增：

## Phase 3：RX 鏈路調整
### 新增或修改 block
- {block_name}

### 參數明細（完整欄位）
#### Block: {block_name} ({block_id})
| 欄位名稱 | 計劃值 |
|---|---|
|  |  |

### Python block 程式碼（若本 phase 修改 Python block）
#### Block: {block_name} ({block_id})
- 原始碼來源：{.grc Embedded Python Block / 外部 Python 檔案路徑}
- 套用方式：以「完整替換程式碼」整段取代該 block 原始碼；「程式碼差異」僅供審閱。

#### 行號與變更摘要
| 原始行號 | 新版行號 | 變更說明 |
|---|---|---|
| L{start}-L{end} | L{start}-L{end} | {說明此區塊修改目的} |

#### 程式碼差異
修改前（L{old_start}-L{old_end}）：
```python
{修改前程式碼}
```

修改後（L{new_start}-L{new_end}，可直接複製）：
```python
{修改後程式碼}
```

### 連線調整
- 移除：
- 新增：

## 驗證計劃
1. 所有 touched blocks 是否提供完整參數
2. 所有參數是否有來源可追溯
3. 是否存在任何猜測值
4. 是否已列出所有新增/移除 connection
5. 是否符合繁體中文與命名規範
6. 若修改 Python block，是否列出行號摘要、程式碼差異與完整替換程式碼

## 阻塞與待確認
- 項目：
- 目前狀態：
- 需要的補充資訊：

## 附錄：查證來源
- 本地來源：
- 網路來源：
