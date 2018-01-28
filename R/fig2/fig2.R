# Read tsv files:
setwd("E:/Documents/School/Distributed Systems/distributed-systems-dragon-arena/R/fig2")
server_0_num = read.table(file = 'server_0_num.tsv', sep = '\t', header = FALSE)
server_1_num = read.table(file = 'server_1_num.tsv', sep = '\t', header = FALSE)

dataframe_server_0 = data.frame(server_0_num)
dataframe_server_1 = data.frame(server_1_num)

#Make arrays same length by adding zeros
dataframe_server_0[seq(nrow(dataframe_server_0), nrow(dataframe_server_1)),1] = 0

dataframe = data.frame(dataframe_server_0, dataframe_server_1)

library(reshape)
library(ggplot2)
ggplot(data=dataframe_server_0, aes(x=seq(1,130), y=seq(1,130))) +
  geom_path(data=dataframe_server_0, aes(V1), colour="lightsalmon3") +  
  geom_path(data=dataframe_server_1, aes(V1), colour="steelblue2") +
  coord_flip() +
  labs(y = "Tick", x = "Number of Clients") +
  geom_hline(yintercept=24, linetype="dashed", color = "grey40") +
  geom_hline(yintercept=52, linetype="dashed", color = "grey40") +
  scale_y_continuous(breaks = seq(0, 130, by=10), expand = c(0, 0), limits = c(0, 140)) +
  scale_x_continuous(expand = c(0, 0), limits = c(0, 8), breaks = c(0.0, 2, 4, 6, 8)) + 
  theme(panel.background = element_blank())
  