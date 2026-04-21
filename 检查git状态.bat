@echo off
chcp 65001 >nul
echo ========================================
echo 检查 Git 状态和大文件
echo ========================================
echo.

echo [1] 检查 .gitignore 是否生效...
echo.
git status --short
echo.

echo [2] 检查是否有大文件将被提交...
echo.
git ls-files | xargs ls -lh 2>nul | findstr /R "[0-9][0-9]M [0-9][0-9][0-9]M"
if errorlevel 1 (
    echo ✓ 没有发现大文件将被提交
) else (
    echo ✗ 警告：发现大文件！请检查 .gitignore
)
echo.

echo [3] 检查模型文件是否被正确忽略...
echo.
if exist "模型训练\训练输出\best_model.pt" (
    git check-ignore "模型训练\训练输出\best_model.pt" >nul 2>&1
    if errorlevel 1 (
        echo ✗ 警告：best_model.pt 未被忽略！
    ) else (
        echo ✓ best_model.pt 已被正确忽略
    )
) else (
    echo ℹ best_model.pt 不存在（正常，应从网盘下载）
)
echo.

echo [4] 检查 node_modules 是否被忽略...
echo.
if exist "网页\legal-ai-web\node_modules" (
    git check-ignore "网页\legal-ai-web\node_modules" >nul 2>&1
    if errorlevel 1 (
        echo ✗ 警告：node_modules 未被忽略！
    ) else (
        echo ✓ node_modules 已被正确忽略
    )
) else (
    echo ℹ node_modules 不存在（需要运行 npm install）
)
echo.

echo [5] 预计提交的文件数量...
echo.
git ls-files | find /c /v ""
echo.

echo ========================================
echo 检查完成！
echo ========================================
echo.
echo 提示：
echo - 如果发现大文件，请更新 .gitignore
echo - 提交前请确保已填写 README 中的网盘链接
echo - 使用 'git add .' 添加所有文件
echo - 使用 'git commit -m "消息"' 提交
echo.
pause
