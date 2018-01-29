# Read tsv files:
setwd("/Users/ZakariasNL/Documents/STUDY/Master/Distributed-Systems/LAB/distributed-systems-dragon-arena/distributed-systems-dragon-arena/R/fig3/")
server_0_num <- read.table(file = 'server_0_num.tsv', sep = '\t', header = FALSE)
server_1_num <- read.table(file = 'server_1_num.tsv', sep = '\t', header = FALSE)
server_2_num <- read.table(file = 'server_2_num.tsv', sep = '\t', header = FALSE)

# Create total
dataframe_total = data.frame(server_0_num$V1 + server_1_num$V1 + server_2_num$V1)

# Convert to dataframe
dataframe_all = data.frame(server_0_num, server_1_num, server_2_num, dataframe_total)
dataframe_all["Tick"] = seq(1, length(server_0_num$V1))
colnames(dataframe_all) = c("Server 0", "Server 1", "Server 2", 
                              "Total", "Tick")

# Create melt
dataframe_melt = melt(dataframe_all, id.vars = "Tick")

# Plot
library(ggplot2)
ggplot(dataframe_melt) +
  geom_path(aes(x=Tick, y=value, color=variable)) +
  scale_color_manual(values = c("steelblue2", "lightsalmon3", "yellowgreen", "tomato")) +
  labs(y = "Tick", x = "Number of Clients") +
  scale_y_continuous(breaks = seq(0, 100, by=20), limits = c(0, 100)) +
  scale_x_continuous(breaks = seq(0, 540, by=100)) +
  theme(panel.background = element_blank()) +
  guides(colour = guide_legend(override.aes = list(size=2)))
