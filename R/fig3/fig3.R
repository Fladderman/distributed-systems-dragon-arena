# Read tsv files:
server_0_num <- read.table(file = 'server_0_num.tsv', sep = '\t', header = FALSE)
server_1_num <- read.table(file = 'server_1_num.tsv', sep = '\t', header = FALSE)
server_2_num <- read.table(file = 'server_2_num.tsv', sep = '\t', header = FALSE)

# convert to dataframe
dataframe_server_0 <- data.frame(server_0_num)
dataframe_server_1 <- data.frame(server_1_num)
dataframe_server_2 <- data.frame(server_2_num)

# create total
dataframe_total <- data.frame(V1 = rep(NA, nrow(server_0_num)))
dataframe_total$V1 <- dataframe_server_0$V1 + dataframe_server_1$V1 + dataframe_server_2$V1

library(ggplot2)
ggplot(data=dataframe_server_0, aes(x=seq(1,523), y=seq(1,523))) +
  geom_path(data=dataframe_server_0, aes(V1), colour="steelblue2") +  
  geom_path(data=dataframe_server_1, aes(V1), colour="lightsalmon3") +
  geom_path(data=dataframe_server_2, aes(V1), colour="yellowgreen") +
  geom_path(data=dataframe_total, aes(V1), colour="tomato") +
  coord_flip() +
  labs(y = "Tick", x = "Number of Clients") +
  scale_y_continuous(breaks = seq(0, 550, by=100)) +
  scale_x_continuous(breaks = seq(0, 110, by=20), limits = c(0, 140)) +
  theme(panel.background = element_blank())
