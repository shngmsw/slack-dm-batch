// グローバル状態管理
const AppState = {
    currentStep: 1,
    slackToken: '',
    targetUsers: [],
    messageTemplate: '',
    userVariables: {},
    sendJobId: null
};

// DOM要素の取得
const DOM = {
    // ステップ要素
    steps: document.querySelectorAll('.step'),
    
    // Step 1
    slackTokenInput: document.getElementById('slack-token'),
    validateTokenBtn: document.getElementById('validate-token'),
    tokenStatus: document.getElementById('token-status'),
    nextStep1Btn: document.getElementById('next-step-1'),
    
    // Step 2
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    mentionsInput: document.getElementById('mentions-input'),
    parseMentionsBtn: document.getElementById('parse-mentions'),
    fileUpload: document.getElementById('file-upload'),
    fileDropZone: document.getElementById('file-drop-zone'),
    usersPreview: document.getElementById('users-list'),
    nextStep2Btn: document.getElementById('next-step-2'),
    
    // Step 3
    messageTemplate: document.getElementById('message-template'),
    variablesDetected: document.getElementById('variables-detected'),
    templateErrors: document.getElementById('template-errors'),
    messagePreview: document.getElementById('message-preview'),
    nextStep3Btn: document.getElementById('next-step-3'),
    
    // Step 4
    variablesSection: document.getElementById('variables-section'),
    noVariables: document.getElementById('no-variables'),
    userVariablesContainer: document.getElementById('user-variables'),
    importVariablesBtn: document.getElementById('import-variables'),
    variablesFile: document.getElementById('variables-file'),
    nextStep4Btn: document.getElementById('next-step-4'),
    
    // Step 5
    sendSummary: document.getElementById('send-summary'),
    finalMessagePreview: document.getElementById('final-message-preview'),
    startSendBtn: document.getElementById('start-send'),
    sendProgress: document.getElementById('send-progress'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    sendResults: document.getElementById('send-results'),
    resultsSummary: document.getElementById('results-summary'),
    resultsDetails: document.getElementById('results-details'),
    
    // 共通
    notification: document.getElementById('notification'),
    loading: document.getElementById('loading')
};

// イベントリスナーの設定
function initEventListeners() {
    // Step 1
    DOM.validateTokenBtn.addEventListener('click', validateToken);
    DOM.nextStep1Btn.addEventListener('click', () => goToStep(2));
    
    // Navigation buttons
    document.getElementById('prev-step-2').addEventListener('click', () => goToStep(1));
    document.getElementById('prev-step-3').addEventListener('click', () => goToStep(2));
    document.getElementById('prev-step-4').addEventListener('click', () => goToStep(3));
    document.getElementById('prev-step-5').addEventListener('click', () => goToStep(4));
    
    // Step 2
    DOM.tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => switchTab(e.target.dataset.tab));
    });
    DOM.parseMentionsBtn.addEventListener('click', parseMentions);
    DOM.fileUpload.addEventListener('change', handleFileUpload);
    setupFileDropZone();
    DOM.nextStep2Btn.addEventListener('click', () => goToStep(3));
    
    // Step 3
    DOM.messageTemplate.addEventListener('input', handleTemplateChange);
    DOM.nextStep3Btn.addEventListener('click', () => goToStep(4));
    
    // Step 4
    DOM.importVariablesBtn.addEventListener('click', () => DOM.variablesFile.click());
    DOM.variablesFile.addEventListener('change', importVariables);
    DOM.nextStep4Btn.addEventListener('click', () => goToStep(5));
    
    // Step 5
    DOM.startSendBtn.addEventListener('click', startSending);
    document.getElementById('retry-send').addEventListener('click', retrySending);
    document.getElementById('reset-app').addEventListener('click', resetApplication);
}

// ユーティリティ関数
function showNotification(message, type = 'success') {
    DOM.notification.textContent = message;
    DOM.notification.className = `notification ${type} show`;
    setTimeout(() => {
        DOM.notification.classList.remove('show');
    }, 4000);
}

function showLoading(show = true) {
    DOM.loading.style.display = show ? 'flex' : 'none';
}

function goToStep(stepNumber) {
    AppState.currentStep = stepNumber;
    DOM.steps.forEach((step, index) => {
        step.classList.toggle('active', index === stepNumber - 1);
    });
    
    if (stepNumber === 4) {
        setupVariablesStep();
    } else if (stepNumber === 5) {
        setupFinalStep();
    }
}

// Step 1: トークン検証
async function validateToken() {
    const token = DOM.slackTokenInput.value.trim();
    if (!token) {
        showStatus(DOM.tokenStatus, 'トークンを入力してください', 'error');
        return;
    }
    
    if (!token.startsWith('xoxp-')) {
        showStatus(DOM.tokenStatus, 'User tokenはxoxp-で始まる必要があります', 'error');
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch('/api/parse-mentions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: '@test', token })
        });
        
        if (response.ok) {
            AppState.slackToken = token;
            showStatus(DOM.tokenStatus, '✓ トークンが有効です', 'success');
            DOM.nextStep1Btn.disabled = false;
        } else {
            const error = await response.json();
            showStatus(DOM.tokenStatus, `エラー: ${error.detail}`, 'error');
        }
    } catch (error) {
        showStatus(DOM.tokenStatus, `接続エラー: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status ${type}`;
}

// Step 2: タブ切り替え
function switchTab(tabName) {
    DOM.tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    DOM.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
}

// Step 2: メンション解析
async function parseMentions() {
    const text = DOM.mentionsInput.value.trim();
    if (!text) {
        showNotification('メンションを入力してください', 'warning');
        return;
    }
    
    showLoading(true);
    try {
        const response = await fetch('/api/parse-mentions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, token: AppState.slackToken })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            AppState.targetUsers = result.users;
            updateUsersPreview();
            
            if (result.errors.length > 0) {
                showNotification(`一部のユーザーが見つかりませんでした: ${result.errors.join(', ')}`, 'warning');
            } else {
                showNotification(`${result.users.length}人のユーザーを取得しました`, 'success');
            }
        } else {
            showNotification(`エラー: ${result.detail}`, 'error');
        }
    } catch (error) {
        showNotification(`接続エラー: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// ファイルドロップゾーンの設定
function setupFileDropZone() {
    DOM.fileDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        DOM.fileDropZone.classList.add('dragover');
    });
    
    DOM.fileDropZone.addEventListener('dragleave', () => {
        DOM.fileDropZone.classList.remove('dragover');
    });
    
    DOM.fileDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        DOM.fileDropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            DOM.fileUpload.files = files;
            handleFileUpload();
        }
    });
}

// ファイルアップロード処理
async function handleFileUpload() {
    const file = DOM.fileUpload.files[0];
    if (!file) return;
    
    showLoading(true);
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/import-variables', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // ユーザーデータの処理（簡略版 - 実際のユーザー解決は後で実装）
            showNotification(`${result.imported_count}件のデータをインポートしました`, 'success');
            
            if (result.errors.length > 0) {
                showNotification(`警告: ${result.errors.join(', ')}`, 'warning');
            }
        } else {
            showNotification(`エラー: ${result.detail}`, 'error');
        }
    } catch (error) {
        showNotification(`ファイル処理エラー: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// ユーザープレビュー更新
function updateUsersPreview() {
    DOM.usersPreview.innerHTML = '';
    
    if (AppState.targetUsers.length === 0) {
        DOM.usersPreview.innerHTML = '<p>送信対象ユーザーがありません</p>';
        DOM.nextStep2Btn.disabled = true;
        return;
    }
    
    AppState.targetUsers.forEach((user, index) => {
        const userItem = document.createElement('div');
        userItem.className = 'user-item';
        userItem.innerHTML = `
            <div class="user-info">
                <div class="user-avatar">${user.display_name.charAt(0).toUpperCase()}</div>
                <div>
                    <div class="user-name">${user.display_name}</div>
                    <div class="user-id" style="font-size: 0.8rem; color: #718096;">@${user.name}</div>
                </div>
            </div>
            <button class="remove-user" onclick="removeUser(${index})">削除</button>
        `;
        DOM.usersPreview.appendChild(userItem);
    });
    
    DOM.nextStep2Btn.disabled = false;
}

// ユーザー削除
function removeUser(index) {
    AppState.targetUsers.splice(index, 1);
    updateUsersPreview();
    showNotification('ユーザーを削除しました', 'success');
}

// Step 3: テンプレート変更処理
function handleTemplateChange() {
    const template = DOM.messageTemplate.value;
    AppState.messageTemplate = template;
    
    if (!template.trim()) {
        DOM.nextStep3Btn.disabled = true;
        DOM.variablesDetected.innerHTML = '';
        DOM.templateErrors.innerHTML = '';
        DOM.messagePreview.innerHTML = '';
        return;
    }
    
    // 変数抽出（簡易版）
    const variables = extractVariables(template);
    
    // UI更新
    if (variables.length > 0) {
        DOM.variablesDetected.innerHTML = `
            <div class="status success">
                検出された変数: ${variables.map(v => `{${v}}`).join(', ')}
            </div>
        `;
    } else {
        DOM.variablesDetected.innerHTML = '<div class="status">変数が検出されませんでした</div>';
    }
    
    // プレビュー表示（サンプル）
    const samplePreview = template.replace(/\{(\w+)\}/g, (match, varName) => {
        return `[${varName.toUpperCase()}]`;
    });
    DOM.messagePreview.textContent = samplePreview;
    
    DOM.nextStep3Btn.disabled = false;
}

// 変数抽出関数
function extractVariables(template) {
    const matches = template.match(/\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g);
    if (!matches) return [];
    
    const variables = matches.map(match => match.slice(1, -1));
    return [...new Set(variables)]; // 重複除去
}

// Step 4: 変数設定ステップ
function setupVariablesStep() {
    const variables = extractVariables(AppState.messageTemplate);
    
    if (variables.length === 0) {
        DOM.variablesSection.style.display = 'none';
        DOM.noVariables.style.display = 'block';
        return;
    }
    
    DOM.variablesSection.style.display = 'block';
    DOM.noVariables.style.display = 'none';
    
    // ユーザーごとの変数入力フィールドを生成
    DOM.userVariablesContainer.innerHTML = '';
    
    AppState.targetUsers.forEach(user => {
        const userVarDiv = document.createElement('div');
        userVarDiv.className = 'user-variable-item';
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'user-variable-header';
        headerDiv.innerHTML = `
            <div class="user-avatar">${user.display_name.charAt(0).toUpperCase()}</div>
            <span>${user.display_name} (@${user.name})</span>
        `;
        
        const inputsDiv = document.createElement('div');
        inputsDiv.className = 'variable-inputs';
        
        variables.forEach(variable => {
            const inputDiv = document.createElement('div');
            inputDiv.className = 'variable-input';
            inputDiv.innerHTML = `
                <label>${variable}</label>
                <input type="text" data-user="${user.id}" data-variable="${variable}" 
                       placeholder="${variable}の値を入力">
            `;
            inputsDiv.appendChild(inputDiv);
        });
        
        userVarDiv.appendChild(headerDiv);
        userVarDiv.appendChild(inputsDiv);
        DOM.userVariablesContainer.appendChild(userVarDiv);
    });
    
    // 変数入力のイベントリスナー
    DOM.userVariablesContainer.addEventListener('input', updateUserVariables);
}

// ユーザー変数の更新
function updateUserVariables() {
    const inputs = DOM.userVariablesContainer.querySelectorAll('input[data-user][data-variable]');
    AppState.userVariables = {};
    
    inputs.forEach(input => {
        const userId = input.dataset.user;
        const variable = input.dataset.variable;
        const value = input.value.trim();
        
        if (!AppState.userVariables[userId]) {
            AppState.userVariables[userId] = {};
        }
        
        if (value) {
            AppState.userVariables[userId][variable] = value;
        }
    });
}

// 変数データのインポート
async function importVariables() {
    const file = DOM.variablesFile.files[0];
    if (!file) return;
    
    showLoading(true);
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/import-variables', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // 変数データをフォームに反映
            Object.entries(result.user_data).forEach(([identifier, variables]) => {
                // ユーザーIDまたは名前で一致するユーザーを探す
                const user = AppState.targetUsers.find(u => 
                    u.id === identifier || u.name === identifier || u.display_name === identifier
                );
                
                if (user) {
                    Object.entries(variables).forEach(([varName, varValue]) => {
                        const input = document.querySelector(`input[data-user="${user.id}"][data-variable="${varName}"]`);
                        if (input) {
                            input.value = varValue;
                        }
                    });
                }
            });
            
            updateUserVariables();
            showNotification('変数データをインポートしました', 'success');
        } else {
            showNotification(`エラー: ${result.detail}`, 'error');
        }
    } catch (error) {
        showNotification(`インポートエラー: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Step 5: 最終確認ステップ
async function setupFinalStep() {
    // 送信サマリー
    DOM.sendSummary.innerHTML = `
        <div class="status">
            <strong>送信対象:</strong> ${AppState.targetUsers.length}人<br>
            <strong>テンプレート:</strong> ${extractVariables(AppState.messageTemplate).length}個の変数を使用
        </div>
    `;
    
    // 最終プレビュー
    showLoading(true);
    try {
        const response = await fetch('/api/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template: AppState.messageTemplate,
                user_data: AppState.userVariables
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            let previewHTML = '';
            AppState.targetUsers.forEach(user => {
                const renderedMessage = result.rendered_messages[user.id] || AppState.messageTemplate;
                previewHTML += `
                    <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px;">
                        <strong>To: ${user.display_name}</strong><br>
                        <div style="margin-top: 10px; font-family: monospace; background: #f7fafc; padding: 10px; border-radius: 4px;">
                            ${renderedMessage}
                        </div>
                    </div>
                `;
            });
            DOM.finalMessagePreview.innerHTML = previewHTML;
            
            if (result.missing_variables.length > 0) {
                showNotification(`警告: 一部の変数が設定されていません: ${result.missing_variables.join(', ')}`, 'warning');
            }
        }
    } catch (error) {
        DOM.finalMessagePreview.textContent = 'プレビューの生成に失敗しました';
    } finally {
        showLoading(false);
    }
}

// Step 5: 送信開始
async function startSending() {
    if (!confirm('メッセージを送信しますか？この操作は元に戻せません。')) {
        return;
    }
    
    showLoading(true);
    DOM.startSendBtn.disabled = true;
    
    try {
        const response = await fetch('/api/send-messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template: AppState.messageTemplate,
                users: AppState.targetUsers,
                user_data: AppState.userVariables,
                token: AppState.slackToken
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            AppState.sendJobId = result.job_id;
            DOM.sendProgress.style.display = 'block';
            showNotification('送信を開始しました', 'success');
            
            // 進捗監視開始
            monitorSendProgress();
        } else {
            showNotification(`送信開始エラー: ${result.detail}`, 'error');
            DOM.startSendBtn.disabled = false;
        }
    } catch (error) {
        showNotification(`送信エラー: ${error.message}`, 'error');
        DOM.startSendBtn.disabled = false;
    } finally {
        showLoading(false);
    }
}

// 送信進捗の監視
async function monitorSendProgress() {
    if (!AppState.sendJobId) return;
    
    try {
        const response = await fetch(`/api/status/${AppState.sendJobId}`);
        const result = await response.json();
        
        if (response.ok) {
            const progress = ((result.sent_count + result.failed_count) / result.total_users) * 100;
            DOM.progressFill.style.width = `${progress}%`;
            DOM.progressText.textContent = `${result.sent_count + result.failed_count} / ${result.total_users} 完了 (成功: ${result.sent_count}, 失敗: ${result.failed_count})`;
            
            if (result.status === 'completed' || result.status === 'failed') {
                showSendResults(result);
            } else {
                // 1秒後に再チェック
                setTimeout(monitorSendProgress, 1000);
            }
        }
    } catch (error) {
        console.error('Progress monitoring error:', error);
        setTimeout(monitorSendProgress, 1000);
    }
}

// 送信結果の表示
function showSendResults(result) {
    DOM.sendProgress.style.display = 'none';
    DOM.sendResults.style.display = 'block';
    
    DOM.resultsSummary.innerHTML = `
        <div class="status ${result.status === 'completed' ? 'success' : 'error'}">
            <strong>送信完了</strong><br>
            総数: ${result.total_users}人<br>
            成功: ${result.sent_count}人<br>
            失敗: ${result.failed_count}人
        </div>
    `;
    
    if (result.errors.length > 0) {
        let errorsHTML = '<h4>エラー詳細</h4><div class="error-details">';
        
        // エラーコード別にグループ化
        const groupedErrors = {};
        result.errors.forEach(error => {
            const code = error.error_code || 'unknown';
            if (!groupedErrors[code]) {
                groupedErrors[code] = [];
            }
            groupedErrors[code].push(error);
        });
        
        // 各エラーコードグループを表示
        Object.entries(groupedErrors).forEach(([errorCode, errors]) => {
            const firstError = errors[0];
            const userNames = errors.map(e => e.user_name || e.user_id).join(', ');
            
            errorsHTML += `
                <div class="error-group">
                    <div class="error-header">
                        <strong>${errorCode}: ${errors.length}人が失敗</strong>
                        <span class="toggle-detail" onclick="toggleErrorDetail('${errorCode}')">詳細を表示 ▼</span>
                    </div>
                    <div class="error-users">対象ユーザー: ${userNames}</div>
                    <div id="detail-${errorCode}" class="error-detail" style="display: none;">
                        <div class="detailed-message">${firstError.detailed_error || firstError.error}</div>
                    </div>
                </div>
            `;
        });
        
        errorsHTML += '</div>';
        DOM.resultsDetails.innerHTML = errorsHTML;
    }
    
    const message = result.status === 'completed' ? 
        `送信が完了しました (成功: ${result.sent_count}, 失敗: ${result.failed_count})` :
        '送信中にエラーが発生しました';
    
    showNotification(message, result.status === 'completed' ? 'success' : 'error');
    
    // ボタンの表示制御
    DOM.startSendBtn.style.display = 'none';
    document.getElementById('retry-send').style.display = 'inline-flex';
    document.getElementById('reset-app').style.display = 'inline-flex';
}

// 送信の再実行
async function retrySending() {
    if (!confirm('送信を再実行しますか？失敗したユーザーのみに再送信されます。')) {
        return;
    }
    
    // 失敗したユーザーのみに絞り込み
    // 実際の実装ではAPI側で失敗リストを管理する必要がありますが、
    // ここでは全ユーザーに再送信として簡易実装
    
    // UIリセット
    DOM.sendResults.style.display = 'none';
    DOM.sendProgress.style.display = 'block';
    DOM.progressFill.style.width = '0%';
    DOM.progressText.textContent = '準備中...';
    
    document.getElementById('retry-send').style.display = 'none';
    document.getElementById('reset-app').style.display = 'none';
    
    // 送信実行（元の関数を再利用）
    await startSending();
}

// アプリケーションのリセット
function resetApplication() {
    if (!confirm('最初からやり直しますか？入力した内容は全て失われます。')) {
        return;
    }
    
    // 状態をリセット
    AppState.currentStep = 1;
    AppState.slackToken = '';
    AppState.targetUsers = [];
    AppState.messageTemplate = '';
    AppState.userVariables = {};
    AppState.sendJobId = null;
    
    // UI要素をリセット
    DOM.slackTokenInput.value = '';
    DOM.tokenStatus.innerHTML = '';
    DOM.nextStep1Btn.disabled = true;
    
    DOM.mentionsInput.value = '';
    DOM.usersPreview.innerHTML = '';
    DOM.nextStep2Btn.disabled = true;
    
    DOM.messageTemplate.value = '';
    DOM.variablesDetected.innerHTML = '';
    DOM.templateErrors.innerHTML = '';
    DOM.messagePreview.innerHTML = '';
    DOM.nextStep3Btn.disabled = true;
    
    DOM.userVariablesContainer.innerHTML = '';
    
    DOM.sendSummary.innerHTML = '';
    DOM.finalMessagePreview.innerHTML = '';
    DOM.sendProgress.style.display = 'none';
    DOM.sendResults.style.display = 'none';
    DOM.startSendBtn.style.display = 'inline-flex';
    DOM.startSendBtn.disabled = false;
    document.getElementById('retry-send').style.display = 'none';
    document.getElementById('reset-app').style.display = 'none';
    
    // Step 1に戻る
    goToStep(1);
    
    showNotification('アプリケーションをリセットしました', 'success');
}

// エラー詳細の表示切り替え
function toggleErrorDetail(errorCode) {
    const detail = document.getElementById(`detail-${errorCode}`);
    const toggle = document.querySelector(`[onclick="toggleErrorDetail('${errorCode}')"]`);
    
    if (detail.style.display === 'none') {
        detail.style.display = 'block';
        toggle.textContent = '詳細を非表示 ▲';
    } else {
        detail.style.display = 'none';
        toggle.textContent = '詳細を表示 ▼';
    }
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    goToStep(1);
});