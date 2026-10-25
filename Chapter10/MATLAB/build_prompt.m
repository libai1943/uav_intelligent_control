function prompt = build_prompt(userText, outputPath, contextPath)
% 第10章完整提示词生成器；仅拼接文本，不联网、不调用模型、不控制设备。
% 交互：build_prompt
% 非交互：p = build_prompt('先去东库，再去西库。');
% 可指定输出路径与教师维护的场景资料路径。
% 兼容目标：MATLAB R2022b。运行说明与测试范围见README。
    root = fileparts(mfilename('fullpath'));
    defaultText = '三个仓库都看一下，先去东库，然后北库，最后西库。今天不开放的就跳过，拍普通照片。';
    if nargin < 1
        if usejava('desktop')
            answer = inputdlg('请输入任务要求（课堂示例，无真实执行）：', ...
                '第10章提示词生成器', [4 90], {defaultText});
            if isempty(answer)
                prompt = '';
                return;
            end
            userText = answer{1};
        else
            userText = input('请输入任务要求（回车使用示例）：', 's');
            if isempty(strtrim(userText)), userText = defaultText; end
        end
    end
    if nargin < 2 || isempty(outputPath)
        outputPath = fullfile(root, 'complete_prompt_matlab.txt');
    end
    if nargin < 3 || isempty(contextPath)
        contextPath = fullfile(root, 'assets', 'context_demo.txt');
    end
    if isstring(userText) && isscalar(userText), userText = char(userText); end
    if ~ischar(userText) || ~isrow(userText) || isempty(strtrim(userText))
        error('Chapter10:Input', '请输入非空的单段文本。');
    end
    if strlength(string(userText)) > 6000
        error('Chapter10:Length', '本教学工具最多接受6000个字符。');
    end
    template = readUtf8(fullfile(root, 'assets', 'prompt_template.txt'));
    context = readUtf8(contextPath);
    if isempty(strtrim(context)), error('Chapter10:Context', '场景资料不能为空。'); end
    if numel(strfind(template, '{{CONTEXT}}')) ~= 1 || ...
       numel(strfind(template, '{{USER_REQUEST_JSON}}')) ~= 1
        error('Chapter10:Template', '模板占位符不完整或重复。');
    end
    if contains(context, '{{USER_REQUEST_JSON}}')
        error('Chapter10:Context', '场景资料含有保留的模板占位符。');
    end
    % JSON转义只明确文本边界，不构成对提示注入的安全保证。
    prompt = strrep(template, '{{CONTEXT}}', [strtrim(context), newline]);
    prompt = strrep(prompt, '{{USER_REQUEST_JSON}}', jsonencode(strtrim(userText)));
    folder = fileparts(outputPath);
    if ~isempty(folder) && ~isfolder(folder), mkdir(folder); end
    [fid, msg] = fopen(outputPath, 'w', 'n', 'UTF-8');
    if fid < 0, error('Chapter10:Write', '无法创建文件：%s', msg); end
    cleanup = onCleanup(@() fclose(fid));
    fprintf(fid, '%s', prompt);
    clear cleanup;
    fprintf('%s\n\n已保存：%s\n本程序没有调用任何模型。\n', prompt, outputPath);
end

function text = readUtf8(path)
    [fid, msg] = fopen(path, 'r', 'n', 'UTF-8');
    if fid < 0, error('Chapter10:Read', '无法读取文件：%s', msg); end
    cleanup = onCleanup(@() fclose(fid));
    text = fscanf(fid, '%c');
    if ~isempty(text) && double(text(1)) == 65279, text = text(2:end); end
end
