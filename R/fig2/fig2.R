# Read tsv files:
#setwd("E:/Documents/School/Distributed Systems/distributed-systems-dragon-arena/R/fig2")
setwd("/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig2")
server_0_num = read.table(file = 'server_0_num.tsv', sep = '\t', header = FALSE)
server_1_num = read.table(file = 'server_1_num.tsv', sep = '\t', header = FALSE)

dataframe_server_0 = data.frame(server_0_num)
dataframe_server_1 = data.frame(server_1_num)

#Make arrays same length by adding zeros
dataframe_server_0[seq(nrow(dataframe_server_0), nrow(dataframe_server_1)),1] = 0

dataframe = data.frame(dataframe_server_0, dataframe_server_1)
dataframe["Tick"] = seq(0, length(dataframe_server_0$V1)-1)
colnames(dataframe) = c("Server 0", "Server 1", "Tick")

dataframe_melt = melt(dataframe, id.vars = "Tick")

library(reshape)
library(ggplot2)
ggplot(dataframe_melt) +
  geom_path(aes(x=Tick, y=value, color=variable)) +
  labs(y = "Number of Clients", x = "Tick") +
  geom_vline(xintercept=24, linetype="dashed", color = "grey40") +
  geom_vline(xintercept=52, linetype="dashed", color = "grey40") +
  scale_y_continuous(breaks = seq(0, 8, by=2), expand = c(0, 0), limits = c(0, 8)) +
  scale_x_continuous(breaks = seq(0, 130, by=10), expand = c(0, 0), limits = c(0, 130)) + 
  theme(panel.background = element_blank())
  