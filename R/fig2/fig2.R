# Read tsv files:
server_0_num = read.table(file = 'server_0_num.tsv', sep = '\t', header = TRUE)
server_1_num = read.table(file = 'server_1_num.tsv', sep = '\t', header = TRUE)

dataframe_server_0 = data.frame(server_0_num)
dataframe_server_1 = data.frame(server_1_num)

#Make arrays same length by adding zeros
dataframe_server_0[seq(nrow(dataframe_server_0), nrow(dataframe_server_1)),1] = 0

dataframe = data.frame(dataframe_server_0, dataframe_server_1)

library(reshape)
library(ggplot2)
ggplot(data=dataframe_server_0, aes(x=seq(1,129), y=seq(1,129))) +
  geom_path(data=dataframe_server_0, aes(X0), colour="lightsalmon3") +  
  geom_path(data=dataframe_server_1, aes(X0), colour="steelblue2") +
  coord_flip() +
  xlim(0, 10) +
  ylim(0, 129) +
  labs(y = "Tick", x = "Number of Clients") +
  scale_y_continuous(breaks = seq(0, 129, by=10)) +
  theme(panel.background = element_blank())

