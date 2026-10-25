% One entry: construct and verify the textbook's complete prompt.
here=fileparts(mfilename('fullpath'));addpath(here);
request='三个仓库都看一下，先去东库，然后北库，最后西库。今天不开放的就跳过，拍普通照片。';
p=build_prompt(request,fullfile(here,'results','complete_prompt.txt'));
assert(contains(p,'【固定输出格式】'));
assert(~contains(p,'{{CONTEXT}}'));
assert(~contains(p,'{{USER_REQUEST_JSON}}'));
fprintf('Chapter 10 prompt construction checks passed.\n');
