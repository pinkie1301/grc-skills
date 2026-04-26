---
name: grc-planner
description: '將 GNU Radio .grc 修改需求正規化為可執行的繁體中文計劃書。當使用者提到修改 grc、調整 flowgraph、重接 block、補參數、寫 implementation plan、比較現有連線與新方案時使用。會輸出標準檔名 plan_{計劃書標題}.md，並強制對所有新增/修改 block 做完整參數查證，禁止猜測欄位。'
---

# GRC 計劃書正規化技能

## 目的
把使用者對 .grc 的修改需求，轉成一份可直接執行的 Markdown 計劃書。

此技能的核心原則：
- 只輸出繁體中文計劃書
- 計劃書檔名固定規則：plan_{title_name}.md
- 所有新增或修改到的 block，必須列出完整參數
- 若修改 Python block / Embedded Python Block，必須直接給出可複製貼上的完整程式碼段落
- 不可猜測 block 欄位、功能、可選參數
- 任何不確定點都必須先查證（本地與網路），查不到就明確標示阻塞

## 觸發時機
當使用者出現以下意圖時使用：
- 要求修改 .grc 或 flowgraph
- 要求先寫計劃書再動手改圖
- 要求重接 TX/RX 鏈路、加入或移除 block
- 要求補齊每個 block 參數與驗證步驟
- 要求把既有方法正規化為通用流程

## 產出物
- 一份計劃書檔案 (最小化計劃書標題)：plan_{title_name}.md
- 內容格式依照本技能模板：[計劃書模板](./assets/plan_template_zh_tw.md)

## 檔名正規化規則
1. 固定前綴：plan_
2. 主體：{title_name}
3. 版本尾碼 (有持續跟進修正才需要，例如: v1, v2, v3...)：_{version}.md
4. 標題中的空白改為底線 _
5. 移除不適合作為檔名的符號（例如 \\ / : * ? " < > |）

範例：
- 原標題：QPSK FEC 1/2 鏈路重接
- 檔名：plan_QPSK_FEC_1_2_鏈路重接_v1.md

## 作業流程

### 第 1 步：需求定義
1. 讀取使用者目標、限制與範圍（例如只改某個 .grc）。
2. 明確列出不在範圍內的項目（例如不改 EPY block 原始碼）。
3. 若需求缺關鍵資訊，先提最少量澄清問題。
4. 若範圍包含 Python block / Embedded Python Block 原始碼修改，將該 block 的程式碼列為 touched artifact。

### 第 2 步：現況盤點
1. 讀取目標 .grc，建立以下清單：
- 現有相關變數
- 現有相關 block（name、id）
- 現有相關 connections
2. 抽出關鍵鏈路錨點（TX、RX、header、payload、tag 相關路徑）。
3. 對照使用者提供的現況症狀（例如 access code 無法解、輸出少一半）。

### 第 3 步：不確定性審核（強制）
對每個將被新增或修改的 block，逐一審核：
1. block 功能是否已確認
2. 欄位名稱是否完整且精確
3. 每個欄位可選值與限制是否已確認
4. 與相鄰 block 的資料型別、tag 行為是否一致
5. 計劃書是否列出該 block 的完整 parameters 區塊欄位（非僅列常用欄位）

block 參數查證一律委派給 `grc-block-query`，不得自行重寫或分散搜尋邏輯。查詢順序：
1. 先查看 `grc-block-query` 的 shared DB root：`~/Documents/grc-block-query/db`
2. block 快取檔路徑固定為：`~/Documents/grc-block-query/db/blocks/{canonical_id}.json`（也就是 `db/blocks/*.json`）
3. 查 block 完整參數時，使用 `grc-block-query` 的查詢流程；本技能只引用查證結果，不自行推論欄位。

若 shared DB 沒有對應 block JSON：
1. 先檢查 `grc-block-query` skill 是否存在於可用 skills 目錄。
2. 若未安裝，停止該 block 查證並提示使用者先安裝 `grc-block-query` skill。
3. 若已安裝，啟用或依照 `grc-block-query` skill，執行查詢腳本：
- 從 repo 根目錄：`python ./skills/grc-block-query/scripts/query_grc_blocks.py --block <block name>`
- 從 `grc-block-query` skill root：`python ./scripts/query_grc_blocks.py --block <block name>`
4. 若只需單一欄位，可加上 `--field "<field name>"`；若要完整 parameters，省略 `--field`。
5. 查詢成功且 `source` 不是 `local-db` 時，必須確認 JSON output 含 `db_file`，表示已回寫 shared DB。
6. 若查詢結果為 `not_found`，或無法取得完整 GUI `parameters:` 欄位，必須把該 block 列入「阻塞與待確認」，不得猜測。

計劃書中每個 touched block 的完整參數表，必須引用 `grc-block-query` JSON output：
- `status`
- `source`
- `source_location`
- `entry.fields` 或 `__grc_parameters__`
- `db_file`（若外部查證後已回寫）

可補充使用專案中現有 .grc、README、設計筆記作為情境佐證；但 block 欄位名稱、可選值、預設值與完整 parameters 仍以 `grc-block-query` 查證結果為準。

### 第 4 步：方案分解
1. 先給高層設計（資料流、訊號同步、調變策略、封包邊界策略...等等）。
2. 再拆成 phase（例如變數、TX、RX、驗證）。
3. 每個 phase 必須包含：
- 具體修改目標
- 要新增/修改的 block 清單
- 每個 block 的完整參數
- 若修改 Python block / Embedded Python Block：完整可貼上的 Python 程式碼段落（使用 fenced code block 標示 `python`）
- 要移除與新增的 connection 清單
- 風險點與回退策略

### 第 5 步：計劃書撰寫
1. 依模板輸出完整計劃書。
2. 計劃書中的所有欄位值，都要能追溯到查證來源。
3. 若仍有未確認項目，必須放在「阻塞與待確認」章節，不能用猜測值填入。
4. 每個 touched block 必須以「完整欄位表」呈現：
- 欄位名稱
- 計劃值
- 來源依據（本地或網路）
- 是否有可選值限制
5. 若修改 Python block / Embedded Python Block，必須在對應 phase 內新增「Python block 程式碼」小節：
- 明確標示 block name / id
- 提供完整替換程式碼，不只描述差異
- 使用 ```python fenced code block，讓使用者可直接複製貼上
- 程式碼內不得省略 import、class/function 定義、必要狀態變數或註解掉的 TODO
- 若缺少現有 Python block 原始碼而無法產生完整替換版本，列入「阻塞與待確認」，不得只給片段或猜測實作

### 第 6 步：品質門檻檢查
送出前逐條檢查：
1. 是否使用繁體中文
2. 檔名是否符合 plan_{title_name}.md
3. 是否包含完整 phase 與驗證清單
4. 是否列出所有 touched blocks 的完整參數
5. 若修改 Python block，是否提供完整可複製貼上的 Python 程式碼段落
6. 是否零猜測（未確認即標示阻塞）
7. 是否包含可重現的驗證與故障排除步驟

## 分支決策規則
- 若需求明確且資訊完整：直接產出完整計劃書
- 若 block 參數資訊不足：先查證，不可跳步
- 若查證後仍不完整：停止編寫該段參數，改列阻塞與提問
- 若使用者要求快速版：可縮短敘述，但不得刪除參數完整性與驗證章節

## 禁止事項
- 禁止臆測 block 欄位名稱
- 禁止使用未驗證的可選參數
- 禁止省略 touched blocks 的參數表
- 禁止只描述 Python block 修改而不提供可複製貼上的完整程式碼段落
- 禁止用省略號、片段或「同上」表示 Python block 替換碼
- 禁止把未確認資訊寫成既定事實
- 禁止以「同預設值」帶過欄位；未查證預設值不得直接採用

## 建議搭配資源
- 模板檔：[計劃書模板](./assets/plan_template_zh_tw.md)
