# Lesson 01 测验结果：Hook 的作用边界存在混淆

Q1 错、Q2 错（选 A）、Q3 对。

Q1 和 Q2 共同暴露一个误解：认为 hook 可以控制 Claude 的输出风格或内容，或者把"可靠行为"写进指令文件就够了。实际上 hook 只管 shell 命令的触发时机，不影响 Claude 怎么回答。

**Implications:** 下一课需要通过动手写 hook 来强化边界感——亲手写一个 Stop hook 和一个 SKILL.md 指令，对比两者的实际效果。
