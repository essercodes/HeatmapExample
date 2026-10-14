FROM ubuntu:latest

ENV LANG=C.UTF-8

RUN if id "ubuntu" &>/dev/null; then \
        echo "Deleting user 'ubuntu'" && userdel -f -r ubuntu || echo "Failed to delete ubuntu user"; \
    else \
         echo "User 'ubuntu' does not exist"; \
    fi;

RUN apt-get update && apt-get install -y sudo

ARG USERNAME=max
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ARG NON_ADMIN_USERNAME=nonAdmin
ARG NON_ADMIN_USER_UID=1001
ARG NON_ADMIN_USER_GID=$NON_ADMIN_USER_UID
ARG SHARED_GROUP_NAME="project"
ARG SHARED_GROUP_GID=1002

# Create the non-admin user
RUN groupadd --gid $NON_ADMIN_USER_GID $NON_ADMIN_USERNAME \
    && useradd --uid $NON_ADMIN_USER_UID --gid $NON_ADMIN_USER_GID --shell /bin/bash -m $NON_ADMIN_USERNAME

# Create the admin user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --shell /bin/bash -m $USERNAME

# Add users to shared group
RUN groupadd --gid $SHARED_GROUP_GID $SHARED_GROUP_NAME
RUN gpasswd -a $USERNAME $SHARED_GROUP_NAME
RUN gpasswd -a $NON_ADMIN_USERNAME $SHARED_GROUP_NAME

# Add sudoers support
ARG SUDOERS_FILE=/etc/sudoers.d/10-${USERNAME}-runas
RUN cat > $SUDOERS_FILE <<EOF && \
    chmod 0440 $SUDOERS_FILE && \
    visudo -c -f $SUDOERS_FILE
$USERNAME ALL=(root) NOPASSWD:ALL
$USERNAME ALL=($NON_ADMIN_USERNAME:$NON_ADMIN_USERNAME) NOPASSWD:ALL
$USERNAME ALL=($NON_ADMIN_USERNAME:$SHARED_GROUP_NAME) NOPASSWD:ALL
EOF

# Set the default user
USER $USERNAME
