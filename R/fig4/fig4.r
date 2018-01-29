# Read tsv files:
#setwd("E:/Documents/School/Distributed Systems/distributed-systems-dragon-arena/R/fig4/")
server_work = read.table(file = '/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig4/server_0_work.tsv', sep = '\t', header = FALSE)

dataframe_server = data.frame(server_work)
mean_work = mean(dataframe_server$V1)

library(ggplot2)
ggplot(data=dataframe_server, aes(x=seq(1, 699), y=seq(1, 699))) +
  geom_point(data=dataframe_server, aes(y=V1), colour="royalblue3", size=0.5) +
  labs(y="Work Time", x="Tick") +
  scale_y_continuous(breaks = seq(0, 180, by=20), 
                     expand = c(0, 0), 
                     limits = c(0, 170)) +
  #geom_hline(yintercept=mean_work, linetype="dashed", color = "grey40") +
  theme(panel.background = element_rect(fill = NA),
        panel.grid.minor = element_line(color = "white"))


