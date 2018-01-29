# Read tsv files:
#setwd("E:/Documents/School/Distributed Systems/distributed-systems-dragon-arena/R/fig4/")
server_work_0 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_0_work.tsv', sep = '\t', header = FALSE)
server_work_1 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_1_work.tsv', sep = '\t', header = FALSE)
server_work_2 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_2_work.tsv', sep = '\t', header = FALSE)
server_work_3 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_3_work.tsv', sep = '\t', header = FALSE)
server_work_4 = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig6/server_4_work.tsv', sep = '\t', header = FALSE)

length_0 = length(server_work_0$V1)
server_work_2 = data.frame(V1=c(0, server_work_2$V1[0:length(server_work_2$V1)]))

server_dataframe = data.frame(server_work_0, server_work_1, server_work_2, 
                              server_work_3, server_work_4)

server_dataframe["Tick"] = seq(1, length_0)
colnames(server_dataframe) = c("Server 0", "Server 1", "Server 2", "Server 3", "Server 4", "Tick")

server_melt = melt(server_dataframe, id.vars = "Tick")

library(ggplot2)
ggplot(server_melt) +
  geom_point(aes(x=Tick, y=value, color=variable), size=0.3) +
  labs(y="Work Time", x="Tick") +
  scale_y_continuous(breaks = seq(0, 160, by=20), 
                     expand = c(0, 0), 
                     limits = c(0, 160)) +
  scale_x_continuous(breaks = seq(0, 600, by=100)) +
  scale_color_manual(values = c("firebrick2", "limegreen", "royalblue4", 
                                "yellow", "lightsalmon3")) +
  theme(panel.background = element_rect(fill = NA),
        panel.grid.minor = element_line(color = "white")) +
  guides(colour = guide_legend(override.aes = list(size=3)))