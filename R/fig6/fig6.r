# Read tsv files:
#setwd("E:/Documents/School/Distributed Systems/distributed-systems-dragon-arena/R/fig4/")
server_work_0 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_0_work.tsv', sep = '\t', header = FALSE)
server_work_1 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_1_work.tsv', sep = '\t', header = FALSE)
server_work_2 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_2_work.tsv', sep = '\t', header = FALSE)
server_work_3 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_3_work.tsv', sep = '\t', header = FALSE)
server_work_4 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_4_work.tsv', sep = '\t', header = FALSE)

length_0 = length(server_work_0$V1)
server_work_2 = data.frame(V1=c(0, server_work_2$V1[0:length(server_work_2$V1)]))

library(ggplot2)
ggplot(data=server_work_0, aes(x=seq(1, length_0), y=seq(1, length_0), label=TRUE, abbr=TRUE)) +
  geom_point(data=server_work_0, aes(y=V1), colour="royalblue3", size=0.5) +
  geom_point(data=server_work_1, aes(y=V1), colour="red", size=0.5) +
  geom_point(data=server_work_2, aes(y=V1), colour="yellowgreen", size=0.5) +
  geom_point(data=server_work_3, aes(y=V1), colour="green", size=0.5) +
  geom_point(data=server_work_4, aes(y=V1), colour="magenta4", size=0.5) +
  labs(y="Work Time", x="Tick") +
  scale_y_continuous(breaks = seq(0, 180, by=20), 
                     expand = c(0, 0), 
                     limits = c(0, 170)) +
  theme(panel.background = element_rect(fill = NA),
        panel.grid.minor = element_line(color = "white"))
